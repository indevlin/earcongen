"""Platform-aware filesystem locations and version resolution."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

APP_NAME = "earcongen"

#: Subdirectory created under the chosen output base.
DEFAULT_OUTPUT_DIRNAME = "earcons"

#: Placed beside a frozen binary to keep settings and output next to the
#: executable instead of in the user profile.
PORTABLE_MARKER = "earcongen-portable.txt"


def is_frozen() -> bool:
    """Whether this is running from a PyInstaller bundle."""
    return getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS")


def resource_root() -> Path:
    """PyInstaller's extraction directory, or the repository root."""
    if is_frozen():
        return Path(sys._MEIPASS)  # type: ignore[attr-defined]
    return Path(__file__).resolve().parent.parent


def binary_dir() -> Path:
    """The directory holding the running executable or entry script."""
    if is_frozen():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def is_portable() -> bool:
    """Whether a portable marker sits beside the binary."""
    try:
        return (binary_dir() / PORTABLE_MARKER).is_file()
    except OSError:
        return False


def read_version() -> str:
    """Read the `version` file, or return "0".

    Bundled into the binary by packaging/build_common.py, so a frozen
    build reports the datestamp it was tagged with.
    """
    for candidate in (resource_root() / "version", binary_dir() / "version"):
        try:
            text = candidate.read_text().strip()
        except OSError:
            continue
        if text:
            return text
    return "0"


def _windows_documents() -> Path:
    # The fallback covers stripped CI environments.
    profile = os.environ.get("USERPROFILE")
    base = Path(profile) if profile else Path.home()
    return base / "Documents"


def _windows_appdata() -> Path:
    appdata = os.environ.get("APPDATA")
    return Path(appdata) if appdata else Path.home() / "AppData" / "Roaming"


def config_dir() -> Path:
    """Settings directory: Roaming AppData, Application Support, or
    $XDG_CONFIG_HOME."""
    if is_portable():
        return binary_dir() / "config"
    if sys.platform == "win32":
        return _windows_appdata() / APP_NAME
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / APP_NAME
    xdg = os.environ.get("XDG_CONFIG_HOME")
    base = Path(xdg) if xdg else Path.home() / ".config"
    return base / APP_NAME


def settings_file() -> Path:
    """The JSON file holding the last-used settings."""
    return config_dir() / "settings.json"


def default_output_base() -> Path:
    """Output base offered on a first run.

    Documents on Windows and macOS; on Linux $XDG_DOCUMENTS_DIR if set
    and present, then ~/Documents, ~/Music, and finally the home
    directory.
    """
    if is_portable():
        return binary_dir() / DEFAULT_OUTPUT_DIRNAME
    if sys.platform == "win32":
        return _windows_documents() / APP_NAME
    if sys.platform == "darwin":
        return Path.home() / "Documents" / APP_NAME

    xdg_docs = os.environ.get("XDG_DOCUMENTS_DIR")
    if xdg_docs:
        candidate = Path(os.path.expandvars(xdg_docs)).expanduser()
        if candidate.is_dir():
            return candidate / APP_NAME
    for candidate in (Path.home() / "Documents", Path.home() / "Music"):
        if candidate.is_dir():
            return candidate / APP_NAME
    return Path.home() / APP_NAME


def reveal(path: Path) -> bool:
    """Open a directory in the platform file manager.

    Returns False instead of raising; a headless host has no file
    manager to open.
    """
    target = path if path.is_dir() else path.parent
    try:
        if sys.platform == "win32":
            os.startfile(str(target))  # type: ignore[attr-defined]
            return True
        command = ["open"] if sys.platform == "darwin" else ["xdg-open"]
        # Detached, so the file manager outlives this process and its
        # output stays out of our streams.
        subprocess.Popen(
            command + [str(target)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=sys.platform != "win32",
        )
        return True
    except (OSError, AttributeError):
        return False
