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

- Data (chats, settings, keys): `~/Library/Application Support/orama`
- Engine log: `~/Library/Application Support/orama/logs/engine.log`
- An optional `.env` file can go in that data folder too.
