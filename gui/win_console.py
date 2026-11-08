"""Making standard output usable on Windows GUI builds.

The binary is built with ``console=False``, which puts it in the Windows
GUI subsystem: it starts with no console attached, PyInstaller leaves
``sys.stdout`` and ``sys.stderr`` unusable, printed output vanishes and
flushing at exit raises ``OSError: [Errno 22] Invalid argument``. The
``--cli`` commands need those streams.

Two cases are reconnected:

*Redirected* — ``EarconGen.exe --cli version > out.txt``, or output
captured by a shell. Valid standard handles were inherited at creation
and only need rewrapping as Python file objects.

*Interactive* — run from an existing console, with no inherited handles.
The process attaches to its parent's console and uses the handles that
produces.

No-op off Windows.
"""

from __future__ import annotations

import os
import sys

#: Passed to AttachConsole to mean "the console of my parent process".
ATTACH_PARENT_PROCESS = -1

#: GetStdHandle selectors.
STD_OUTPUT_HANDLE = -11
STD_ERROR_HANDLE = -12

#: What GetStdHandle returns when there is no handle to give.
INVALID_HANDLE_VALUE = 2**64 - 1


def _is_usable(stream: object) -> bool:
    """Whether ``stream`` can be written to.

    A windowed build may leave it None or holding an invalid descriptor.
    """
    if stream is None:
        return False
    fileno = getattr(stream, "fileno", None)
    if fileno is None:
        return False
    try:
        return fileno() >= 0
    except (OSError, ValueError):
        return False


def enable_console_output() -> bool:
    """Reconnect ``sys.stdout`` and ``sys.stderr`` on Windows.

    Returns True when both streams end up usable. Never raises; the
    caller runs regardless.
    """
    if sys.platform != "win32":
        return True

    if _is_usable(sys.stdout) and _is_usable(sys.stderr):
        return True

    try:
        import ctypes
        import msvcrt
    except ImportError:  # pragma: no cover - Windows only
        return False

    try:
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        # Declared explicitly: a HANDLE is pointer-sized and ctypes'
        # default int return type truncates it on 64-bit Windows.
        kernel32.GetStdHandle.argtypes = [ctypes.c_uint32]
        kernel32.GetStdHandle.restype = ctypes.c_void_p
        kernel32.AttachConsole.argtypes = [ctypes.c_uint32]
        kernel32.AttachConsole.restype = ctypes.c_bool

        def std_handle(selector: int) -> int | None:
            handle = kernel32.GetStdHandle(ctypes.c_uint32(selector & 0xFFFFFFFF))
            if not handle or handle == INVALID_HANDLE_VALUE:
                return None
            return handle

        # Read the existing handles before touching the console:
        # AttachConsole replaces them with the console's own, which would
        # redirect inherited pipe or file output to the console instead.
        handles = {
            "stdout": std_handle(STD_OUTPUT_HANDLE),
            "stderr": std_handle(STD_ERROR_HANDLE),
        }

        if handles["stdout"] is None and handles["stderr"] is None:
            # Nothing inherited: launched from a console without
            # redirection. Fails harmlessly when the parent has none.
            kernel32.AttachConsole(ctypes.c_uint32(ATTACH_PARENT_PROCESS & 0xFFFFFFFF))
            handles = {
                "stdout": std_handle(STD_OUTPUT_HANDLE),
                "stderr": std_handle(STD_ERROR_HANDLE),
            }

        for name, handle in handles.items():
            if handle is None or _is_usable(getattr(sys, name, None)):
                continue
            descriptor = msvcrt.open_osfhandle(handle, os.O_WRONLY)
            stream = os.fdopen(
                descriptor,
                "w",
                buffering=1,
                encoding="utf-8",
                errors="replace",
                closefd=False,
            )
            setattr(sys, name, stream)
    except (OSError, ValueError, AttributeError):  # pragma: no cover
        return False

    return _is_usable(sys.stdout) and _is_usable(sys.stderr)


__all__ = [
    "ATTACH_PARENT_PROCESS",
    "STD_ERROR_HANDLE",
    "STD_OUTPUT_HANDLE",
    "enable_console_output",
]
