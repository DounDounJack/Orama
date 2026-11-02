"""órama engine entry point (the hidden server inside the desktop app).

Started by the Tauri shell, never by the user. Settings come from the
environment the shell passes in:

  ORAMA_PORT          port to listen on (127.0.0.1 only)
  ORAMA_LAUNCH_TOKEN  one-time token the window uses to get in (desktop_gate)
  ORAMA_DATA_DIR      where chats, settings and keys live
  ORAMA_PARENT_PID    the shell's process id; the engine exits if it goes away

PyInstaller freezes this file into the `orama-engine` program.
"""
import multiprocessing
import os
import sys
import threading
import time


class _NullWriter:
    def write(self, text):
        pass

    def flush(self):
        pass

    def isatty(self):
        return False


def _watch_parent(pid: int, on_gone):
    """Stop the engine if the órama window process dies without cleaning up."""
    while True:
        time.sleep(2)
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            on_gone()
            return
        except PermissionError:
            pass  # exists, owned by someone else (shouldn't happen)
        if os.getppid() == 1:  # re-parented to launchd/init: our parent is gone
            on_gone()
            return


def main():
    if sys.stdout is None:
        sys.stdout = _NullWriter()
    if sys.stderr is None:
        sys.stderr = _NullWriter()

    port = int(os.environ.get("ORAMA_PORT") or "0")
    token = os.environ.get("ORAMA_LAUNCH_TOKEN", "")
    if not port or not token:
        print("orama-engine is started by the órama app, not directly.", file=sys.stderr)
        sys.exit(2)

    data_dir = os.environ.get("ORAMA_DATA_DIR", "").strip()
    if data_dir:
        os.makedirs(data_dir, exist_ok=True)
        os.environ["ODYSSEUS_DATA_DIR"] = data_dir
        os.chdir(data_dir)  # so an optional .env in the data folder is read

    # The engine must know its own port for agent-tool loopback calls.
    os.environ["APP_PORT"] = str(port)
    os.environ["APP_BIND"] = "127.0.0.1"
    os.environ["LOCALHOST_BYPASS"] = "false"
    # Desktop app: never expect Docker-only services.
    os.environ.pop("CHROMADB_HOST", None)
    os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")

    if not getattr(sys, "frozen", False):
        # Running from source: make the repo root importable.
        root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        sys.path.insert(0, root)

    import uvicorn
    from app import app
    from core.middleware import INTERNAL_TOOL_TOKEN, INTERNAL_TOOL_HEADER
    from src import shutdown as _shutdown
    from src.desktop_gate import DesktopGate

    gated = DesktopGate(app, launch_token=token, internal_token=INTERNAL_TOOL_TOKEN,
                        internal_header=INTERNAL_TOOL_HEADER)

    config = uvicorn.Config(
        gated,
        host="127.0.0.1",
        port=port,
        log_level="info",
        # Closing the window should stop the engine quickly.
        timeout_graceful_shutdown=5,
    )
    server = uvicorn.Server(config)
    _handle_exit = server.handle_exit

    def _on_signal(signum, frame):
        _shutdown.request_shutdown()
        _handle_exit(signum, frame)

    server.handle_exit = _on_signal

    parent = int(os.environ.get("ORAMA_PARENT_PID") or "0")
    if parent:
        def _stop():
            _shutdown.request_shutdown()
            server.should_exit = True
        threading.Thread(target=_watch_parent, args=(parent, _stop), daemon=True).start()

    server.run()


if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
