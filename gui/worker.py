"""Rendering off the interface thread.

The window holds both the worker and its thread for the whole run: a
QThread referenced only by a local is collected while still running and
takes the process down. `finished` drives `quit`, then `deleteLater` on
both, and the window clears its references only once the thread stops.
"""

from __future__ import annotations

import argparse
import traceback
from pathlib import Path

from PySide6.QtCore import QObject, Signal

import earcongen


class GenerateWorker(QObject):
    """Renders one family, reporting each file as it is written."""

    #: path, duration in seconds, contour name, note count, label
    file_written = Signal(Path, float, str, int, str)
    #: index of the cue just finished, and the total
    progress = Signal(int, int)
    #: every file, in order, once the run has succeeded
    finished_ok = Signal(list)
    #: a message suitable for showing the user
    failed = Signal(str)
    #: always emitted last, success or failure
    finished = Signal()

    def __init__(self, args: argparse.Namespace) -> None:
        super().__init__()
        self._args = args
        self._cancelled = False

    def cancel(self) -> None:
        """Request a stop. Checked between cues, never mid-render."""
        self._cancelled = True

    def run(self) -> None:
        try:
            specs = earcongen.resolve_specs(self._args)
            total = len(specs)
            written: list[Path] = []
            index = 0

            def on_file(item: earcongen.Rendered) -> None:
                nonlocal index
                index += 1
                written.append(item.path)
                self.file_written.emit(
                    item.path, item.duration, item.spec.contour,
                    item.notes, item.spec.label,
                )
                self.progress.emit(index, total)
                if self._cancelled:
                    raise _Cancelled

            earcongen.generate_family(self._args, on_file=on_file)
            self.finished_ok.emit(written)

        except _Cancelled:
            self.failed.emit("Cancelled. Files written so far have been kept.")
        except FileNotFoundError as exc:
            self.failed.emit(f"Could not write to that location: {exc}")
        except PermissionError as exc:
            self.failed.emit(f"Permission denied: {exc}")
        except Exception as exc:
            # Traceback to stderr, message to the user.
            traceback.print_exc()
            self.failed.emit(f"{type(exc).__name__}: {exc}")
        finally:
            self.finished.emit()


class _Cancelled(Exception):
    """Unwinds the render loop on cancellation."""
