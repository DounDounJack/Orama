# órama: notes for Claude

## What this is

órama (by Doun Industries) is a modified version of Odysseus
(https://github.com/odysseus-dev/odysseus, imported at commit `8450793`),
licensed AGPL-3.0-or-later. It's a self-hosted AI workspace: a Python FastAPI
backend (`app.py`, `src/`, `routes/`, `services/`, `mcp_servers/`) and a
no-build vanilla JS frontend (`static/`). Today it runs in Docker
(`docker-compose.yml`) and is opened in a browser at http://localhost:7011.

## Who you're working with

- A two-person team: the repo owner and a friend who tests and is a
  collaborator on the GitHub repo.
- The owner develops on a **Mac mini M4 Pro** (Apple Silicon, macOS 26, 24 GB
  RAM, Homebrew, python.org Python 3.14; no Rust or Node yet, no Docker). They
  also have a **Surface Laptop Go 2 running Linux Mint 22** (Docker installed,
  the current Docker install of órama lives there). The friend is on Windows.
- They don't write the code. You write it; they test it and make the calls.
- Talk plainly and briefly. No jargon dumps. When they need to run something,
  give the exact command to copy and paste, and say what they should see.
- Writing anywhere user-facing (README, setup guide, UI text): plain and
  simple, never AI-sounding.

## Already done (don't redo)

All listed in `DOUN-SETUP.md` → "What changed from Odysseus". In short:

- **Theme:** `doun` preset (jet black `#0a0a0a`, orange `#ff7a1a`) is the
  default. Defined in `static/js/theme.js` (`THEMES.doun`, `DEFAULT_THEME`),
  `static/css/00-tokens.css` and `static/login.html`. Keep all three in sync.
  Font is unchanged (Fira Code).
- **Branding:** user-visible "Odysseus" → "Doun Industries". Welcome title
  reads "órama", no tagline. Sidebar top-left still says "Doun Industries".
- **Logo:** `static/icons/logo.svg` (eye + two-tone pyramid). Inline copies:
  `static/index.html` (favicon link, early theme script, welcome title),
  `static/login.html`, `_updateFavicon` in `static/js/theme.js`. App icons:
  `static/icons/icon-*.png`, `static/icon.ico`.
- **Removed features:** Email, Calendar, Gallery, Tasks. Agent tools are
  disabled in `src/doun_features.py` (hooked into `stream_agent_loop` in
  `src/agent_loop.py`; email MCP server skipped in `src/builtin_mcp.py`). UI
  entry points hidden by the block at the bottom of
  `static/css/email-calendar-notes-tasks.css`. Slash commands and shortcuts
  removed in `static/js/slashCommands.js`, `keyboard-shortcuts.js`,
  `settings.js`.
- **Object Detection placeholder:** sidebar/rail entry, window
  `#objdetect-modal` in `static/index.html`, logic in
  `static/js/objectDetection.js` (controls disabled, no model yet).
- **Fixed:** ASCII Fireflies background only filled ~60% of the width on
  Linux/Windows (it measured a Mac-only font). Fix in `_initAsciiFireflies`,
  `static/js/theme.js`.
- **Docker image** renamed to `orama:local` in all `docker-compose*.yml`, so a
  pull can never swap in upstream's published image.
- Upstream's `.github/` folder (their CI, deploy, bots) was left out on
  purpose.
- **Voice assistant:** Voice tab in the persona window (`static/js/voiceProfiles.js`,
  markup in `static/index.html`, hooked into `static/js/presets.js`). Profiles
  live on personas/templates as `voice` (`src/voice_profiles.py`: model, prompt
  builder, starter styles Steward/Sunny/Brief/Mentor; `routes/voice_routes.py`).
  `/api/tts/synthesize` takes an optional `voice`/`speed`; `tts-ai.js` uses the
  active persona's voice via `window.oramaGetActiveVoice`. Talk mode is
  `static/js/talkMode.js` (button `#talk-mode-btn`). Starter styles must stay
  original: nothing named after or copying a film/TV/book character.
  Local Kokoro TTS needs CUDA, so on the Mac use the system voices (Settings →
  Speech → Browser) or an API voice; speech-to-text there should be Local
  (Whisper), since the app window has no browser speech recognition.
- **UI testing without Node:** Playwright for Python works in `.venv`
  (`pip install playwright && python -m playwright install chromium`); use
  `bypass_csp=True` on the browser context, because the app's CSP blocks
  Playwright's string evaluation.

## Rules

- Keep `LICENSE` (AGPL), `ACKNOWLEDGMENTS.md`, `licenses/` and the credit to
  Odysseus and Felix Kjellberg (README + any About screen). The app must stay
  AGPL while Odysseus code is in it.
- Rebrand only what users see. Leave internal names alone: `odysseus` in code
  and imports, `X-Odysseus-*` headers, `odysseus-*` localStorage keys, the
  compose service name `odysseus`, the "Odysseus" character persona, and the
  "Reminder (Odysseus):" email subject (used to find those emails).
- Never commit `data/` or `.env` (chats, logins, API keys). Both are
  gitignored.
- Docker: always `docker compose up -d --build`. Never tell them to run
  `docker compose pull` or `docker compose down -v` (`-v` deletes their data).
- A new JS module loaded by the app must also go in the `PRECACHE` list in
  `static/sw.js` (checked by `tests/test_service_worker_static_cache.py`).
  Imports carry `?v=` cache-busting strings; bump them when you change a file
  that's imported that way.
- Tests live in `tests/` (thousands of them). Run the ones related to the
  files you touch rather than the whole suite.

## Their current install

The Docker install they use day to day is on the **Surface (Linux Mint)** at
`~/doun-industries` (from a zip plus two patch files, so its git history
differs from this repo). This repo is checked out on the Mac at `~/orama`.
On the Surface, their chats, settings and
API keys live in `~/doun-industries/data`, with config in
`~/doun-industries/.env`. To switch to this repo's checkout: stop the old
containers (`docker compose stop` in the old folder), then copy `data/` and
`.env` into this folder before starting.

## Current goal: órama as a real desktop app

Full plan: the "órama desktop app plan" doc on claude.ai. Summary:

**Target:** one installer (.dmg on Mac, .deb/AppImage on Linux, .exe/.msi on
Windows), its own window, no Docker, no browser, no terminal needed. **Build
and test the Mac version first**, on the Mac mini you're running on; Linux and
Windows follow in phase 2, built on GitHub Actions runners. The Odysseus engine
still runs, hidden, as part of the app.

**Architecture:** a Tauri 2 app (Rust) in a new `desktop/` folder. On launch
it starts the engine as a sidecar (the Python app frozen with PyInstaller;
`Odysseus.spec`, `launcher.py` and `build-windows-portable.ps1` are a working
starting point), on a random `127.0.0.1` port with a one-time token so only
órama can talk to it. It waits until the engine answers, shows the UI in its
own window, and stops the engine when the window closes. Data goes in the
OS app-data folder (`~/Library/Application Support/orama` on Mac,
`~/.local/share/orama` on Linux, `%APPDATA%\orama` on Windows), not the app
folder. Odysseus already runs natively on Apple Silicon (`website/setup.md`,
`build-macos-app.sh`).

**Removing Docker:**
- ChromaDB: `src/chroma_client.py` only uses `chromadb.HttpClient` (needs a
  server). Switch to an embedded `chromadb.PersistentClient` under the data
  folder. `website/setup.md` notes that `chromadb-client` and full `chromadb`
  conflict.
- Search: make DuckDuckGo the default (`services/search/`; Brave and Tavily
  work with keys). No SearXNG.
- ntfy: drop it; use Tauri desktop notifications later.

### Phase 1: Mac desktop app

- [x] Tauri project in `desktop/`
- [x] Engine runs natively without Docker (embedded Chroma, DuckDuckGo search, no ntfy)
- [x] Engine packaged with PyInstaller as a Tauri sidecar
- [x] Tauri starts/stops the engine (random port + token), opens the window when ready
- [x] Data in the user's home folder

Built on branch `desktop-app`; see `desktop/README.md`. Waiting on the
owner's test from the Applications folder.

Done when: órama opens from the Mac's Applications folder (or Dock) in its
own window, with no Docker and no terminal. Unsigned is fine for their own use
(Apple signing costs US$99 a year; only needed to share with other Macs).

### Phase 2: Linux, Windows and installers

- [ ] GitHub Actions workflow that builds the Linux .deb/AppImage on an
  Ubuntu runner and the Windows installer on a Windows runner (PyInstaller
  can't cross-compile). Upstream's `.github/` isn't in this repo; write a new one
- [ ] Owner tests the Linux build on the Surface (Linux Mint 22)
- [ ] First-run screen: create login, paste an API key
- [ ] Auto-updates from GitHub releases
- [ ] Friend tests on Windows

### Phase 3: object detection

Run a detection model in Rust with ONNX Runtime (`ort` crate). YOLO (AGPL,
matches órama's licence) or RT-DETR (Apache-2.0). Wire it to the existing
placeholder window, then add an agent tool so chat can ask "what's in this
photo?".

### Phase 4: their own screens

Replace Odysseus screens one at a time with órama's own, talking to the
engine's API. Design calls are theirs: show them before building.

## Handy facts

- Google retired `gemini-2.5-flash` (returns 404); use `gemini-3.5-flash`.
- The Surface runs Linux Mint 22 (Ubuntu 24.04 base), so .deb builds made on
  an Ubuntu 24.04 runner run on it.
- The Surface Laptop Go 2 is a small laptop: keep heavy builds on the Mac or
  GitHub Actions, not on it.
