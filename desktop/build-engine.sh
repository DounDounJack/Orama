#!/bin/bash
# Build the órama engine (frozen Python server) for the desktop app.
#
#   ./desktop/build-engine.sh
#
# Makes desktop/.venv-engine (Python 3.12) if needed, installs the engine's
# packages, and freezes it with PyInstaller into desktop/engine/dist/orama-engine/.
# Needs Python 3.12 (Mac: `brew install python@3.12`).
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
VENV="$HERE/.venv-engine"
PY="${ORAMA_PYTHON:-}"

if [ -z "$PY" ]; then
  for c in python3.12 /opt/homebrew/bin/python3.12 /usr/local/bin/python3.12; do
    if command -v "$c" >/dev/null 2>&1; then PY="$(command -v "$c")"; break; fi
  done
fi
if [ -z "$PY" ]; then
  echo "Python 3.12 not found. On a Mac: brew install python@3.12" >&2
  exit 1
fi

if [ ! -x "$VENV/bin/python" ]; then
  echo "Making build environment with $PY"
  "$PY" -m venv "$VENV"
fi

echo "Installing engine packages"
"$VENV/bin/python" -m pip install -q --upgrade pip
# Full chromadb replaces chromadb-client (they conflict).
REQS="$(mktemp)"
grep -v '^chromadb-client' "$ROOT/requirements.txt" > "$REQS"
"$VENV/bin/python" -m pip install -q -r "$REQS" -r "$HERE/engine/requirements-desktop.txt"
rm -f "$REQS"

echo "Freezing engine (takes a few minutes)"
cd "$HERE/engine"
"$VENV/bin/python" -m PyInstaller --noconfirm --clean \
  --distpath "$HERE/engine/dist" --workpath "$HERE/engine/build" \
  orama-engine.spec

echo "Done: $HERE/engine/dist/orama-engine/orama-engine"
