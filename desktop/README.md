# órama desktop app

The desktop app is a small Tauri (Rust) window that starts the órama engine
in the background, waits for it, and shows it. No Docker, no browser.

## Build on a Mac

One-time setup:

    brew install python@3.12
    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
    cargo install tauri-cli --version "^2" --locked

Then, from the repo folder:

    ./desktop/build-mac.sh

Takes a few minutes. You get:

- `desktop/src-tauri/target/release/bundle/macos/órama.app`
- `desktop/src-tauri/target/release/bundle/dmg/órama_<version>_aarch64.dmg`

If only the Rust or loading-screen parts changed, `./desktop/build-mac.sh
--skip-engine` reuses the last engine build.

## Windows and Linux builds

These are built on GitHub Actions (`.github/workflows/desktop.yml`), since
PyInstaller can't build for another system. Two ways to start one:

- Push a version tag, e.g. `git tag v0.2.1 && git push origin v0.2.1`. This
  builds both and publishes a GitHub pre-release with the installers. Bump
  the version in `src-tauri/tauri.conf.json` and `src-tauri/Cargo.toml` first.
- Actions tab → "Desktop builds" → Run workflow (the button only shows once
  the workflow is on the `main` branch). The installers end up under
  "Artifacts" on the run's page.

Outputs: `orama_<version>_x64-setup.exe` (Windows), `orama_<version>_amd64.deb`
and `orama_<version>_amd64.AppImage` (Linux, built on Ubuntu 22.04 so they
run on Linux Mint 21 and 22). Each build checks that the engine starts, both
before packaging and after installing (`engine/smoke_test.py`).

On Linux the package is named `orama` (Debian package names can't have
accents; see `src-tauri/tauri.linux.conf.json`), but the menu still says órama.

## How it fits together

- `engine/orama_engine.py`: the engine's entry point. Frozen with PyInstaller
  (`engine/orama-engine.spec`, built by `build-engine.sh`).
- `src-tauri/src/main.rs`: picks a free port and a one-time token, starts the
  engine, shows `ui/index.html` until it answers, then opens it in the window.
  Quitting the app stops the engine. If the app crashes, the engine notices
  and stops by itself.
- `../src/desktop_gate.py`: makes the engine refuse anything that isn't the
  órama window.

## Where things live

- Data (chats, settings, keys): `~/Library/Application Support/orama` on Mac,
  `~/.local/share/orama` on Linux, `%APPDATA%\orama` on Windows
- Engine log: `logs/engine.log` inside that folder
- An optional `.env` file can go in that data folder too.
