# Doun Industries — setup

This is Odysseus with the Doun Industries look: jet black with orange, the
órama logo, and an Object Detection section (placeholder for now). Email,
Calendar, Gallery and Tasks are taken out.

It runs in Docker, so it works on Linux, Windows or Mac.

## 1. Install Docker (once)

**Windows or Mac:** install Docker Desktop from https://www.docker.com/products/docker-desktop/,
open it, and leave it running. Then skip to step 2 and type the commands into
PowerShell (Windows) or Terminal (Mac).

**Linux (Mint / Ubuntu):**

```bash
sudo apt update
sudo apt install -y docker.io docker-compose-v2 git
sudo usermod -aG docker $USER
```

Log out and back in so the group change takes effect.

## 2. Start it

Download it from GitHub (or unzip a copy you were given), then go into the
folder:

```bash
git clone https://github.com/DounDounJack/Orama.git orama
cd orama
cp .env.example .env
docker compose up -d --build
```

The first build takes a while (10–20 minutes). When it's done, get your admin
password:

```bash
docker compose logs odysseus | grep -i password
```

On Windows PowerShell use this instead:

```powershell
docker compose logs odysseus | Select-String password
```

Open http://localhost:7011 and log in.

## 3. Connect Claude (Anthropic)

1. Get an API key from https://console.anthropic.com
2. In the app: **Settings → Add Models**
3. Pick **Anthropic** as the provider, paste the key, save
4. Choose a Claude model from the model picker in chat

## 4. Running models on your own machine (optional)

Still there, nothing removed:

- **Cookbook** (sidebar) scans your hardware, suggests models that fit, and
  downloads/serves them.
- Or install Ollama and add it in **Settings → Add Models** as a local endpoint.

If you have an NVIDIA card and want GPU support, start with
`docker compose -f docker-compose.yml -f docker-compose.gpu-nvidia.yml up -d --build`.

## Everyday commands

```bash
docker compose stop            # stop it
docker compose up -d           # start it again
docker compose logs -f odysseus  # watch the logs
```

## Getting updates

When there are new órama changes on GitHub:

```bash
cd orama
git pull
docker compose up -d --build
```

Your chats, settings and login live in the `data` folder, which isn't part of
the repo, so updating never touches them.

Newer Odysseus versions don't come through automatically. This repo started
from a snapshot of Odysseus (commit `8450793`), so bringing in later upstream
fixes means copying them over by hand.

## What changed from Odysseus

- **Theme:** new default "doun industries" preset (`static/js/theme.js`,
  `static/css/00-tokens.css`, `static/login.html`). All the other themes are
  still in the Theme panel.
- **Name:** visible "Odysseus" text replaced with "Doun Industries" across the
  app, login page, tab titles, notifications and desktop launcher.
- **Logo:** the órama eye-and-pyramid mark replaces the sailboat (welcome
  screen, login, browser tab, app icons). Source: `static/icons/logo.svg`.
  The welcome title reads "órama" and the tagline under it is gone.
- **Removed:** Email, Calendar, Gallery and Tasks. Buttons hidden
  (`static/css/email-calendar-notes-tasks.css`, bottom), slash commands and
  shortcuts taken out, and the AI's email/calendar/task tools switched off
  (`src/doun_features.py`). Undo by editing those two places.
- **Object Detection:** new sidebar + icon-rail entry, a window with the layout
  for image input, model picker and results (all disabled for now), a toggle in
  Settings → Appearance, and `/open detect`. Code: `static/js/objectDetection.js`
  and the `objdetect-modal` block in `static/index.html`.
- **ASCII background:** fills the whole screen on Linux/Windows (it measured
  a Mac-only font before). `static/js/theme.js`.
- **Docker image:** named `orama:local` instead of the official Odysseus image,
  so it's always built from this folder (`docker-compose*.yml`).
- **Repo:** upstream's `.github` folder (their CI, website deploy and bots)
  isn't included. Odysseus's own README is in `ODYSSEUS-README.md`.

Left as Odysseus on purpose: internal code names, the AI's background
instructions, the "Odysseus" character persona (alongside Socrates etc.),
reminder-email subjects (used to find and tidy those emails), crash reports
meant for upstream bug reports, and the licence credits.

## Licence

AGPL-3.0-or-later, same as Odysseus. Keep `LICENSE` and `ACKNOWLEDGMENTS.md`.
If anyone other than you uses this over a network, you need to offer them this
source code.
