"""Playing a generated cue from inside the application.

Two backends behind one interface. ``QSoundEffect`` is used when
QtMultimedia is present and reports a working backend; otherwise an
external command-line player is run, since QtMultimedia on Linux needs a
running sound server that may be absent.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

from PySide6.QtCore import QObject, QUrl, Signal

try:  # A separate wheel component, and can be absent.
    from PySide6.QtMultimedia import QSoundEffect
except ImportError:  # pragma: no cover - depends on the install
    QSoundEffect = None  # type: ignore[assignment]


def external_player() -> list[str] | None:
    """First available command-line player, or None.

    ``winsound`` is handled separately, being a module rather than a
    command.
    """
    if sys.platform == "darwin" and shutil.which("afplay"):
        return ["afplay"]
    for command in (["paplay"], ["pw-play"], ["aplay", "-q"],
                    ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet"]):
        if shutil.which(command[0]):
            return command
    return None


class Player(QObject):
    """Plays one file at a time, stopping whatever was already playing."""

    #: Reason playback could not start.
    failed = Signal(str)
    #: Emitted with the path when playback begins.
    started = Signal(Path)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._effect = None
        self._process: subprocess.Popen | None = None
        self._backend = "none"

        if QSoundEffect is not None:
            # Held for the Player's lifetime: a QSoundEffect that goes
            # out of scope stops mid-sample and can crash the process.
            self._effect = QSoundEffect(self)
            self._backend = "qt"
        elif external_player() or sys.platform == "win32":
            self._backend = "external"

    @property
    def backend(self) -> str:
        """Backend in use: ``qt``, ``external`` or ``none``."""
        return self._backend

    def describe(self) -> str:
        """One-line backend description for the status bar."""
        if self._backend == "qt":
            return "audio: Qt"
        if self._backend == "external":
            command = external_player()
            return f"audio: {command[0]}" if command else "audio: system"
        return "audio: unavailable"

    def play(self, path: Path) -> None:
        self.stop()
        if not path.is_file():
            self.failed.emit(f"{path.name} is no longer on disk.")
            return

        if self._effect is not None:
            self._effect.setSource(QUrl.fromLocalFile(str(path)))
            self._effect.setVolume(1.0)
            self._effect.play()
            # A failed load sets an error status rather than raising.
            if self._effect.status() == QSoundEffect.Error:
                self._backend = "external"
                self._play_external(path)
                return
            self.started.emit(path)
            return

        self._play_external(path)

    def _play_external(self, path: Path) -> None:
        if sys.platform == "win32":
            try:
                import winsound

                # SND_ASYNC returns immediately, keeping the UI live.
                winsound.PlaySound(
                    str(path), winsound.SND_FILENAME | winsound.SND_ASYNC
                )
                self.started.emit(path)
                return
            except (ImportError, RuntimeError) as exc:
                self.failed.emit(f"Windows playback failed: {exc}")
                return

        command = external_player()
        if command is None:
            self.failed.emit(
                "No audio backend found. Install a player such as paplay, "
                "aplay or ffplay, or open the output folder and listen there."
            )
            return
        try:
            self._process = subprocess.Popen(
                command + [str(path)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            self.started.emit(path)
        except OSError as exc:
            self.failed.emit(f"Could not start {command[0]}: {exc}")

    def stop(self) -> None:
        if self._effect is not None:
            self._effect.stop()
        if self._process is not None and self._process.poll() is None:
            self._process.terminate()
            try:
                self._process.wait(timeout=1.0)
            except subprocess.TimeoutExpired:  # pragma: no cover
                self._process.kill()
        self._process = None
        if sys.platform == "win32" and self._effect is None:
            try:
                import winsound

                winsound.PlaySound(None, winsound.SND_PURGE)
            except (ImportError, RuntimeError):  # pragma: no cover
                pass
