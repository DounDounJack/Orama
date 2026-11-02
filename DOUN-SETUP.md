# Doun Industries — setup on Linux Mint

This is Odysseus with the Doun Industries look: jet black with orange, same
font, every original feature kept, plus an Object Detection section (placeholder
for now).

## 1. Install Docker (once)

```bash
sudo apt update
sudo apt install -y docker.io docker-compose-v2 git
sudo usermod -aG docker $USER
```

Log out and back in so the group change takes effect.

## 2. Start it

Unzip the folder somewhere (e.g. your home folder), then:

```bash
cd doun-industries
cp .env.example .env
docker compose up -d --build
```

The first build takes a while. When it's done, get your admin password:

```bash
docker compose logs odysseus | grep -i password
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

## Getting Odysseus updates later

This folder is a git repo on a branch called `doun-industries`. To pull in
upstream fixes:

```bash
git fetch --unshallow origin     # first time only
git fetch origin
git merge origin/dev
docker compose up -d --build
```

If a merge clashes, it'll usually be in `static/index.html` or
`static/js/theme.js`.

## What changed from Odysseus

- **Theme:** new default "doun industries" preset (`static/js/theme.js`,
  `static/css/00-tokens.css`, `static/login.html`). All the other themes are
  still in the Theme panel.
- **Name:** visible "Odysseus" text replaced with "Doun Industries" across the
  app, login page, tab titles, notifications and desktop launcher.
- **Object Detection:** new sidebar + icon-rail entry, a window with the layout
  for image input, model picker and results (all disabled for now), a toggle in
  Settings → Appearance, and `/open detect`. Code: `static/js/objectDetection.js`
  and the `objdetect-modal` block in `static/index.html`.

Left as Odysseus on purpose: internal code names, the AI's background
instructions, the "Odysseus" character persona (alongside Socrates etc.),
reminder-email subjects (used to find and tidy those emails), crash reports
meant for upstream bug reports, and the licence credits.

## Licence

AGPL-3.0-or-later, same as Odysseus. Keep `LICENSE` and `ACKNOWLEDGMENTS.md`.
If anyone other than you uses this over a network, you need to offer them this
source code.
