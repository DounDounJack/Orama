# -*- mode: python ; coding: utf-8 -*-
# PyInstaller recipe for the órama engine (the hidden server inside the app).
# Build with desktop/build-engine.sh, not by hand.
#
# Output: dist/orama-engine/ (a folder: the `orama-engine` program plus its
# libraries). The Tauri app ships that whole folder as a resource.

import os
import sys
from PyInstaller.utils.hooks import collect_all, collect_submodules

ROOT = os.path.abspath(os.path.join(SPECPATH, "..", ".."))


def R(*p):
    return os.path.join(ROOT, *p)


# Files the engine reads from its own folder at runtime.
datas = [
    (R("static"), "static"),
    (R("resources"), "resources"),
    (R("scripts"), "scripts"),
    (R("config"), "config"),
    (R("mcp_servers"), "mcp_servers"),
    (R("services", "hwfit", "data"), os.path.join("services", "hwfit", "data")),
    (R("src", "containment_worker.py"), "src"),
    (R("licenses"), "licenses"),
    (R("LICENSE"), "."),
    (R("ACKNOWLEDGMENTS.md"), "."),
    (R("THIRD_PARTY_PROVENANCE.json"), "."),
    (R("HARNESS_VERSION"), "."),
    (R(".env.example"), "."),
]
binaries = []

# The app imports many of its own modules by name at runtime, so include all
# of them rather than relying on import tracing.
hiddenimports = []
for pkg in ("src", "routes", "services", "core", "mcp_servers", "integrations"):
    hiddenimports += collect_submodules(pkg)
hiddenimports += ["app"]

# Third-party packages with data files, native libraries or plugins.
for pkg in (
    "chromadb", "fastembed", "onnxruntime", "tokenizers", "faster_whisper",
    "ctranslate2", "uvicorn", "mcp", "ddgs", "primp", "pypdfium2", "nh3",
    "tiktoken", "tiktoken_ext", "yt_dlp", "certifi", "croniter",
):
    try:
        d, b, h = collect_all(pkg)
    except Exception:
        continue
    datas += d
    binaries += b
    hiddenimports += h

a = Analysis(
    [os.path.join(SPECPATH, "orama_engine.py")],
    pathex=[ROOT],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # Not used by the engine; keeps the bundle smaller.
    excludes=["tkinter", "pystray", "matplotlib", "IPython", "jupyter", "pytest"],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="orama-engine",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    # On Windows a console program would flash a black window for the engine
    # and for every helper it starts, so build it as a windowless program.
    console=(sys.platform != "win32"),
    icon=(R("static", "icon.ico") if sys.platform == "win32" else None),
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="orama-engine",
)
