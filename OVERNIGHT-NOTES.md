# Overnight notes (2 Nov 2026)

## Download

https://github.com/DounDounJack/Orama/releases/tag/v0.2.0 (pre-release)

- Windows: `orama_0.2.0_x64-setup.exe`
- Linux: `orama_0.2.0_amd64.deb` (or the `.AppImage`)
- Mac: `orama_0.2.0_aarch64.dmg`

The repo is private, so you (and your friend) need to be logged in to GitHub
to download.

## What got done

- **Kokoro on the Mac:** there was no unfinished work to pick up. The repo was
  clean, with no saved changes and nothing about kokoro-onnx anywhere, so the
  earlier session's work wasn't saved. Not started this time. It's still to do.
- **Windows and Linux builds work.** New GitHub Actions workflow
  (`.github/workflows/desktop.yml`) builds the Windows installer and the
  Linux .deb and AppImage (on Ubuntu 22.04, so they run on Mint 21 and 22).
- Each build checks that the engine starts and answers, both before packaging
  and after actually installing the package. Passing on both.
- Took 2 tries on Linux (the package name "órama" isn't allowed in a .deb, so
  on Linux the package is called `orama`; the menu still says órama) and 1 on
  Windows. Used roughly 100 of the 2,000 free monthly build minutes.
- Fixed a Windows bug before it bit: the engine's "is the app still open?"
  check would have killed the app on Windows.
- Mac .dmg rebuilt here as 0.2.0. I opened it: the window loads órama and
  quitting stops the engine.
- Everything is on the `desktop-app` branch. `main` is unchanged.

## Please test in the morning

1. **Mac:** open the .dmg and drag órama to Applications. The first time,
   right-click it and choose Open (it's unsigned).
2. **Surface (Linux Mint):** download the .deb, then in a terminal:

       cd ~/Downloads && sudo apt install ./orama_0.2.0_amd64.deb

   Open órama from the menu. It starts fresh (new login). To bring your old
   chats and settings over, close órama, then:

       mkdir -p ~/.local/share/orama && cp -a ~/doun-industries/data/. ~/.local/share/orama/ && cp ~/doun-industries/.env ~/.local/share/orama/

3. **Windows (your friend):** run the setup .exe. Windows will warn because
   it's unsigned: click "More info", then "Run anyway".

On each one, check that the window opens, you can log in, and a chat gets a
reply.

## Still to know

- The builds only test the engine automatically. The window itself on
  Windows and Linux has only been checked on the Mac so far, so your tests
  are the real check.
- The installers in the release come from the last passing test build. The
  v0.2.0 tag build got skipped because of a "[skip ci]" in my last commit
  message (my mistake; the app code is the same). Next time you push a tag
  like `v0.2.1`, the workflow builds and publishes the release by itself.
- The "Run workflow" button in the Actions tab only shows up once
  `desktop-app` is merged into `main`. Tags work either way.
- Phase 2 still to do: first-run screen, auto-updates, Kokoro voice on the Mac.
