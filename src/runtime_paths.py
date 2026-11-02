"""Helpers for resolving runtime paths in source and frozen builds."""

import os
import sys


def get_app_root() -> str:
    """Return the app root directory.

    In normal source runs, this is the repository root. In a frozen Windows
    build, it is the bundle content root (PyInstaller's internal directory)
    so bundled runtime folders like `static/`, `scripts/`, and `data/` stay
    together with the executable payload.
    """
    if getattr(sys, "frozen", False):
        return getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(sys.executable)))
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_user_data_dir(app_name: str = "orama") -> str:
    """Return the OS app-data folder for órama.

    macOS:   ~/Library/Application Support/orama
    Windows: %APPDATA%\\orama
    Linux:   $XDG_DATA_HOME/orama, or ~/.local/share/orama
    """
    home = os.path.expanduser("~")
    if sys.platform == "darwin":
        return os.path.join(home, "Library", "Application Support", app_name)
    if os.name == "nt":
        base = os.environ.get("APPDATA") or os.path.join(home, "AppData", "Roaming")
        return os.path.join(base, app_name)
    base = os.environ.get("XDG_DATA_HOME") or os.path.join(home, ".local", "share")
    return os.path.join(base, app_name)


def get_default_data_dir() -> str:
    """Return the default path to the data directory.

    In normal runs, this is a 'data' subdirectory under the app root.
    In frozen builds (the órama desktop app), it is the OS app-data folder
    (see get_user_data_dir), so SQLite databases and other persistent files
    are never written into the temporary extraction bundle directory.
    The desktop app also passes ODYSSEUS_DATA_DIR explicitly, which wins.
    """
    if getattr(sys, "frozen", False):
        return get_user_data_dir()
    return os.path.join(get_app_root(), "data")
