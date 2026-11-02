// órama desktop app.
//
// On launch: pick a free 127.0.0.1 port and a one-time token, start the
// bundled engine (orama-engine) with them, show a loading screen until the
// engine answers, then point the window at the engine. When the app quits,
// stop the engine.
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::{
    fs,
    io::{Read, Write},
    net::{SocketAddr, TcpListener, TcpStream},
    path::{Path, PathBuf},
    process::{Child, Command, Stdio},
    sync::Mutex,
    thread,
    time::{Duration, Instant},
};

use tauri::{
    AppHandle, Manager, RunEvent, Url, WebviewUrl, WebviewWindowBuilder,
};

const START_TIMEOUT: Duration = Duration::from_secs(240);
const STOP_GRACE: Duration = Duration::from_secs(6);

struct Engine {
    child: Mutex<Option<Child>>,
    port: u16,
    log_path: PathBuf,
}

fn random_token() -> String {
    let mut bytes = [0u8; 32];
    getrandom::getrandom(&mut bytes).expect("random token");
    bytes.iter().map(|b| format!("{b:02x}")).collect()
}

fn free_port() -> std::io::Result<u16> {
    let listener = TcpListener::bind("127.0.0.1:0")?;
    Ok(listener.local_addr()?.port())
}

/// True once the engine answers GET /__orama/ping with "ok".
fn ping(port: u16) -> bool {
    let addr: SocketAddr = ([127, 0, 0, 1], port).into();
    let Ok(mut stream) = TcpStream::connect_timeout(&addr, Duration::from_millis(500)) else {
        return false;
    };
    let _ = stream.set_read_timeout(Some(Duration::from_secs(2)));
    let req = format!(
        "GET /__orama/ping HTTP/1.1\r\nHost: 127.0.0.1:{port}\r\nConnection: close\r\n\r\n"
    );
    if stream.write_all(req.as_bytes()).is_err() {
        return false;
    }
    let mut buf = String::new();
    let _ = stream.read_to_string(&mut buf);
    let body = buf.split_once("\r\n\r\n").map(|(_, b)| b).unwrap_or("");
    buf.starts_with("HTTP/1.1 200") && body.contains("ok")
}

/// The órama data folder: ~/Library/Application Support/orama on Mac,
/// ~/.local/share/orama on Linux, %APPDATA%\orama on Windows.
fn data_dir(app: &AppHandle) -> Result<PathBuf, String> {
    let base = app.path().data_dir().map_err(|e| e.to_string())?;
    Ok(base.join("orama"))
}

/// How to start the engine. ORAMA_ENGINE overrides it for development, e.g.
/// ORAMA_ENGINE="/path/.venv/bin/python /path/desktop/engine/orama_engine.py"
fn engine_command(app: &AppHandle) -> Result<Command, String> {
    if let Ok(dev) = std::env::var("ORAMA_ENGINE") {
        let mut parts = dev.split_whitespace();
        let program = parts.next().ok_or("ORAMA_ENGINE is empty")?;
        let mut cmd = Command::new(program);
        cmd.args(parts);
        return Ok(cmd);
    }
    let exe = if cfg!(windows) { "orama-engine.exe" } else { "orama-engine" };
    let path = app
        .path()
        .resource_dir()
        .map_err(|e| e.to_string())?
        .join("engine")
        .join("orama-engine")
        .join(exe);
    if !path.exists() {
        return Err(format!("The engine is missing from the app ({}).", path.display()));
    }
    Ok(Command::new(path))
}

fn open_log(dir: &Path) -> Result<(fs::File, PathBuf), String> {
    let logs = dir.join("logs");
    fs::create_dir_all(&logs).map_err(|e| e.to_string())?;
    let path = logs.join("engine.log");
    if path.exists() {
        let _ = fs::rename(&path, logs.join("engine.previous.log"));
    }
    let file = fs::File::create(&path).map_err(|e| e.to_string())?;
    Ok((file, path))
}

fn start_engine(app: &AppHandle, token: &str) -> Result<Engine, String> {
    let data = data_dir(app)?;
    fs::create_dir_all(&data).map_err(|e| format!("Can't create {}: {e}", data.display()))?;
    let (log, log_path) = open_log(&data)?;
    let port = free_port().map_err(|e| e.to_string())?;

    let mut cmd = engine_command(app)?;
    cmd.env("ORAMA_PORT", port.to_string())
        .env("ORAMA_LAUNCH_TOKEN", token)
        .env("ORAMA_DATA_DIR", &data)
        .env("ORAMA_PARENT_PID", std::process::id().to_string())
        .current_dir(&data)
        .stdin(Stdio::null())
        .stdout(log.try_clone().map_err(|e| e.to_string())?)
        .stderr(log);
    #[cfg(windows)]
    {
        use std::os::windows::process::CommandExt;
        const CREATE_NO_WINDOW: u32 = 0x0800_0000;
        cmd.creation_flags(CREATE_NO_WINDOW);
    }
    let child = cmd.spawn().map_err(|e| format!("Couldn't start the engine: {e}"))?;
    Ok(Engine { child: Mutex::new(Some(child)), port, log_path })
}

fn stop_engine(app: &AppHandle) {
    let Some(engine) = app.try_state::<Engine>() else { return };
    let Some(mut child) = engine.child.lock().unwrap().take() else { return };
    #[cfg(unix)]
    unsafe {
        // Ask nicely first so the engine can save and stop its helpers.
        libc::kill(child.id() as i32, libc::SIGTERM);
    }
    #[cfg(not(unix))]
    let _ = child.kill();
    let deadline = Instant::now() + STOP_GRACE;
    loop {
        match child.try_wait() {
            Ok(Some(_)) => return,
            Ok(None) if Instant::now() < deadline => thread::sleep(Duration::from_millis(100)),
            _ => {
                let _ = child.kill();
                let _ = child.wait();
                return;
            }
        }
    }
}

fn js_string(s: &str) -> String {
    let mut out = String::from("\"");
    for c in s.chars() {
        match c {
            '"' => out.push_str("\\\""),
            '\\' => out.push_str("\\\\"),
            '\n' => out.push_str("\\n"),
            c if (c as u32) < 0x20 => out.push_str(&format!("\\u{:04x}", c as u32)),
            c => out.push(c),
        }
    }
    out.push('"');
    out
}

fn show_status(app: &AppHandle, text: &str, error: bool, log: Option<&Path>) {
    if let Some(w) = app.get_webview_window("main") {
        let log = log.map(|p| js_string(&p.display().to_string())).unwrap_or("null".into());
        let _ = w.eval(&format!(
            "window.oramaStatus && window.oramaStatus({}, {}, {})",
            js_string(text),
            error,
            log
        ));
    }
}

/// Open a link in the user's normal browser.
fn open_external(url: &Url) {
    let u = url.as_str();
    #[cfg(target_os = "macos")]
    let _ = Command::new("open").arg(u).spawn();
    #[cfg(target_os = "linux")]
    let _ = Command::new("xdg-open").arg(u).spawn();
    #[cfg(windows)]
    let _ = Command::new("cmd").args(["/C", "start", "", u]).spawn();
}

/// Wait for the engine, then show it in the window.
fn wait_and_open(app: AppHandle, port: u16, token: String) {
    thread::spawn(move || {
        let started = Instant::now();
        let mut told_slow = false;
        let log_path = app.state::<Engine>().log_path.clone();
        loop {
            let exited = {
                let engine = app.state::<Engine>();
                let mut guard = engine.child.lock().unwrap();
                match guard.as_mut().map(|c| c.try_wait()) {
                    Some(Ok(Some(status))) => Some(status.to_string()),
                    None => return, // app is quitting
                    _ => None,
                }
            };
            if let Some(status) = exited {
                show_status(
                    &app,
                    &format!("órama's engine stopped while starting ({status})."),
                    true,
                    Some(&log_path),
                );
                return;
            }
            if ping(port) {
                let url = format!("http://127.0.0.1:{port}/__orama/open?token={token}");
                if let (Some(w), Ok(url)) = (app.get_webview_window("main"), Url::parse(&url)) {
                    let _ = w.navigate(url);
                }
                return;
            }
            if !told_slow && started.elapsed() > Duration::from_secs(12) {
                show_status(&app, "Starting… the first start takes a little longer.", false, None);
                told_slow = true;
            }
            if started.elapsed() > START_TIMEOUT {
                show_status(&app, "órama's engine didn't start in time.", true, Some(&log_path));
                return;
            }
            thread::sleep(Duration::from_millis(250));
        }
    });
}

fn main() {
    let app = tauri::Builder::default()
        .setup(|app| {
            let handle = app.handle().clone();
            let token = random_token();

            let engine = start_engine(&handle, &token);
            let port = engine.as_ref().map(|e| e.port).unwrap_or(0);

            WebviewWindowBuilder::new(app, "main", WebviewUrl::App("index.html".into()))
                .title("órama")
                .inner_size(1280.0, 820.0)
                .min_inner_size(720.0, 520.0)
                .center()
                .background_color(tauri::window::Color(10, 10, 10, 255))
                // Keep the window on órama's own pages; open other links in
                // the browser.
                .on_navigation(move |url| {
                    let ours = match url.scheme() {
                        "tauri" | "about" | "data" | "blob" => true,
                        "http" | "https" => {
                            (url.host_str() == Some("127.0.0.1") && url.port() == Some(port))
                                || url.host_str() == Some("tauri.localhost")
                        }
                        _ => false,
                    };
                    if !ours {
                        open_external(url);
                    }
                    ours
                })
                .build()?;

            match engine {
                Ok(engine) => {
                    app.manage(engine);
                    wait_and_open(handle, port, token);
                }
                Err(err) => {
                    let h = handle.clone();
                    // Give the loading page a moment to load before showing the error.
                    thread::spawn(move || {
                        thread::sleep(Duration::from_millis(600));
                        show_status(&h, &err, true, None);
                    });
                }
            }
            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("error while building órama");

    app.run(|handle, event| match event {
        RunEvent::WindowEvent { event: tauri::WindowEvent::Destroyed, .. } => {
            stop_engine(handle);
            handle.exit(0);
        }
        RunEvent::ExitRequested { .. } | RunEvent::Exit => stop_engine(handle),
        _ => {}
    });
}
