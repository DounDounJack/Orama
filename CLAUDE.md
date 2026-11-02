# órama: notes for Claude

## What this is

órama (by Doun Industries) is a modified version of Odysseus
(https://github.com/odysseus-dev/odysseus, imported at commit `8450793`),
licensed AGPL-3.0-or-later. It's a self-hosted AI workspace: a Python FastAPI
backend (`app.py`, `src/`, `routes/`, `services/`, `mcp_servers/`) and a
no-build vanilla JS frontend (`static/`). Today it runs in Docker
(`docker-compose.yml`) and is opened in a browser at http://localhost:7011.

## Who you're working with

- A two-person team: the repo owner (Linux Mint 22, Docker installed) and a
  friend who tests and is a collaborator on the GitHub repo.
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

The owner's working copy is `~/doun-industries` (from a zip plus two patch
files, so its git history differs from this repo). Their chats, settings and
API keys live in `~/doun-industries/data`, with config in
`~/doun-industries/.env`. To switch to this repo's checkout: stop the old
containers (`docker compose stop` in the old folder), then copy `data/` and
`.env` into this folder before starting.

## Current goal: órama as a real desktop app

Full plan: the "órama desktop app plan" doc on claude.ai. Summary:

**Target:** one installer (.deb/AppImage on Linux, .exe/.msi on Windows), its
own window, no Docker, no browser, no terminal needed. The Odysseus engine
still runs, hidden, as part of the app.

**Architecture:** a Tauri 2 app (Rust) in a new `desktop/` folder. On launch
it starts the engine as a sidecar (the Python app frozen with PyInstaller;
`Odysseus.spec`, `launcher.py` and `build-windows-portable.ps1` are a working
starting point), on a random `127.0.0.1` port with a one-time token so only
órama can talk to it. It waits until the engine answers, shows the UI in its
own window, and stops the engine when the window closes. Data goes in
`~/.local/share/orama` (Linux) or `%APPDATA%\orama` (Windows), not the app
folder.

**Removing Docker:**
- ChromaDB: `src/chroma_client.py` only uses `chromadb.HttpClient` (needs a
  server). Switch to an embedded `chromadb.PersistentClient` under the data
  folder. `website/setup.md` notes that `chromadb-client` and full `chromadb`
  conflict.
- Search: make DuckDuckGo the default (`services/search/`; Brave and Tavily
  work with keys). No SearXNG.
- ntfy: drop it; use Tauri desktop notifications later.

### Phase 1: Linux desktop app

- [ ] Tauri project in `desktop/`
- [ ] Engine runs natively without Docker (embedded Chroma, DuckDuckGo search, no ntfy)
- [ ] Engine packaged with PyInstaller as a Tauri sidecar
- [ ] Tauri starts/stops the engine (random port + token), opens the window when ready
- [ ] Data in the user's home folder

Done when: órama opens from the Mint menu in its own window with Docker
turned off.

### Phase 2: installers and Windows

- [ ] .deb and AppImage
- [ ] GitHub Actions workflow that builds the Windows installer on a Windows
  runner (PyInstaller can't cross-compile)
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
- Their machine is Linux Mint 22 (Ubuntu 24.04 base), so .deb builds made on
  Ubuntu 24.04 run on it.
