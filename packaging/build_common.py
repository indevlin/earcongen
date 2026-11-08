"""Shared PyInstaller configuration, imported by ``earcongen.spec``.

QT_EXCLUDES drops the Qt modules the GUI never loads, which roughly
halves the binary. QtMultimedia is kept: it is the in-window playback
backend. numpy is a runtime dependency and must never be excluded.

Qt is LGPL v3 and is never statically linked; PyInstaller bundles it as
shared libraries loaded at runtime. DATA_FILES carries the licence texts
into every binary.
"""

from __future__ import annotations

from pathlib import Path

#: Repository root, derived from this file's own location. PyInstaller
#: injects SPECPATH into the spec's namespace only, not into modules the
#: spec imports, so it cannot be relied on here.
ROOT = Path(__file__).resolve().parent.parent

#: Bundled so a frozen binary can report its version. The release
#: workflow's smoke test compares that output against the tag.
VERSION_FILE = ROOT / "version"

#: Files shipped alongside the code inside the bundle.
DATA_FILES = [
    (str(VERSION_FILE), "."),
    (str(ROOT / "LICENSE"), "."),
    (str(ROOT / "THIRD-PARTY-NOTICES.md"), "."),
    (str(ROOT / "licenses"), "licenses"),
]

#: Qt modules the GUI never loads.
QT_EXCLUDES = [
    "PySide6.Qt3DAnimation",
    "PySide6.Qt3DCore",
    "PySide6.Qt3DExtras",
    "PySide6.Qt3DInput",
    "PySide6.Qt3DLogic",
    "PySide6.Qt3DRender",
    "PySide6.QtBluetooth",
    "PySide6.QtCharts",
    "PySide6.QtDataVisualization",
    "PySide6.QtDesigner",
    "PySide6.QtHelp",
    "PySide6.QtLocation",
    "PySide6.QtNetworkAuth",
    "PySide6.QtNfc",
    "PySide6.QtOpenGL",
    "PySide6.QtOpenGLWidgets",
    "PySide6.QtPdf",
    "PySide6.QtPdfWidgets",
    "PySide6.QtPositioning",
    "PySide6.QtQml",
    "PySide6.QtQuick",
    "PySide6.QtQuick3D",
    "PySide6.QtQuickControls2",
    "PySide6.QtQuickWidgets",
    "PySide6.QtRemoteObjects",
    "PySide6.QtScxml",
    "PySide6.QtSensors",
    "PySide6.QtSerialPort",
    "PySide6.QtSql",
    "PySide6.QtStateMachine",
    "PySide6.QtSvgWidgets",
    "PySide6.QtTest",
    "PySide6.QtTextToSpeech",
    "PySide6.QtWebChannel",
    "PySide6.QtWebEngineCore",
    "PySide6.QtWebEngineQuick",
    "PySide6.QtWebEngineWidgets",
    "PySide6.QtWebSockets",
]

#: Packages that may exist in the build environment but are never
#: imported. numpy is excluded from this list: it is required.
OTHER_EXCLUDES = [
    "IPython",
    "matplotlib",
    "pandas",
    "pytest",
    "scipy",
    "tkinter",
]

EXCLUDES = QT_EXCLUDES + OTHER_EXCLUDES

#: Named explicitly so a missing module fails the build rather than the
#: first run.
HIDDEN_IMPORTS = [
    "earcongen",
    "gui.app",
    "gui.params",
    "gui.paths",
    "gui.player",
    "gui.widgets",
    "gui.worker",
    "gui.win_console",
]


def analysis_kwargs(entry_point: str = "earcongui.py") -> dict:
    """Keyword arguments for a PyInstaller ``Analysis``."""
    return {
        "scripts": [str(ROOT / entry_point)],
        # Repository root: earcongen.py is a top-level module.
        "pathex": [str(ROOT)],
        "binaries": [],
        "datas": DATA_FILES,
        "hiddenimports": list(HIDDEN_IMPORTS),
        "hookspath": [],
        "hooksconfig": {},
        "runtime_hooks": [],
        "excludes": EXCLUDES,
        "noarchive": False,
        "optimize": 0,
    }
