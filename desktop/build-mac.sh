#!/bin/bash
# Build órama.app and órama .dmg for this Mac.
#
#   ./desktop/build-mac.sh              # full build
#   ./desktop/build-mac.sh --skip-engine  # reuse the last engine build
#
# Needs: Rust (rustup), the Tauri CLI (cargo install tauri-cli --version "^2"),
# and Python 3.12 (brew install python@3.12).
# Output: desktop/src-tauri/target/release/bundle/macos/órama.app
#         desktop/src-tauri/target/release/bundle/dmg/órama_<version>_aarch64.dmg
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
[ -f "$HOME/.cargo/env" ] && . "$HOME/.cargo/env"

if [ "${1:-}" != "--skip-engine" ]; then
  "$HERE/build-engine.sh"
fi

ENGINE="$HERE/engine/dist/orama-engine"
if [ ! -x "$ENGINE/orama-engine" ]; then
  echo "No engine build found. Run without --skip-engine." >&2
  exit 1
fi

echo "Copying engine into the app"
STAGE="$HERE/src-tauri/resources/engine"
rm -rf "$STAGE"
mkdir -p "$STAGE"
ditto "$ENGINE" "$STAGE/orama-engine"

echo "Building the app"
cd "$HERE/src-tauri"
# CI=true skips the Finder window-layout step for the .dmg (it hangs without
# Finder automation permission); the .dmg still works the same.
CI=true cargo tauri build

echo
echo "Done:"
ls -d "$HERE"/src-tauri/target/release/bundle/macos/*.app "$HERE"/src-tauri/target/release/bundle/dmg/*.dmg
