"""Shared fixtures and host capability probes."""

from __future__ import annotations

import os
import subprocess
import sys

import pytest

#: Probe source. Enumerating audio outputs and constructing a QSoundEffect
#: are the two calls that abort rather than raise when the host has no
#: usable audio stack, so both run before the probe reports success.
_PROBE = """
from PySide6.QtWidgets import QApplication
app = QApplication([])
from PySide6.QtMultimedia import QMediaDevices, QSoundEffect
QMediaDevices.audioOutputs()
QSoundEffect()
"""

_cached: bool | None = None


def qt_multimedia_usable() -> bool:
    """Whether QtMultimedia initialises without aborting.

    Probed in a subprocess because the failure is a SIGSEGV inside Qt
    rather than a Python exception, so an in-process check would end the
    whole test run. A headless host with no sound server, and a partial
    PipeWire install missing client.conf, both fail this way.

    Cached, so the subprocess runs once per session.
    """
    global _cached
    if _cached is None:
        try:
            done = subprocess.run(
                [sys.executable, "-c", _PROBE],
                capture_output=True,
                timeout=120,
                env={**os.environ, "QT_QPA_PLATFORM": "offscreen"},
            )
            _cached = done.returncode == 0
        except (OSError, subprocess.TimeoutExpired):
            _cached = False
    return _cached


@pytest.fixture(scope="session")
def require_multimedia() -> None:
    """Skip the dependent test unless QtMultimedia is usable."""
    if not qt_multimedia_usable():
        pytest.skip("QtMultimedia cannot be initialised on this host")
