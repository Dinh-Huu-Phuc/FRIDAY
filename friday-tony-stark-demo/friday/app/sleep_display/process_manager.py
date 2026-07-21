from __future__ import annotations

import ctypes
import json
import os
import subprocess
import sys
import time
from ctypes import wintypes
from dataclasses import asdict, dataclass
from pathlib import Path

from friday.app.sleep_display.mutex import named_mutex


WINDOW_TITLE = "FRIDAY Sleep Display"
WM_CLOSE = 0x0010
_FRIDAY_DIR = Path(__file__).resolve().parents[2]
_PROJECT_ROOT = _FRIDAY_DIR.parent
_STATE_PATH = _FRIDAY_DIR / "log" / "runtime" / "sleep_display.json"


@dataclass(frozen=True, slots=True)
class SleepDisplayResult:
    ok: bool
    action: str
    pid: int
    message: str

    def to_dict(self) -> dict[str, str | int | bool]:
        return asdict(self)


def start_sleep_display() -> SleepDisplayResult:
    if not _enabled():
        return SleepDisplayResult(False, "start", 0, "Sleep display is disabled.")
    if os.name != "nt":
        return SleepDisplayResult(False, "start", 0, "Sleep display is available only on Windows.")

    with named_mutex("FRIDAY_SLEEP_DISPLAY_LIFECYCLE"):
        state = _read_state()
        existing_pid = int(state.get("pid") or 0)
        if existing_pid and _find_window(existing_pid):
            return SleepDisplayResult(True, "start", existing_pid, "Sleep display is already running.")
        _STATE_PATH.unlink(missing_ok=True)

        creation_flags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0) | getattr(
            subprocess, "CREATE_NO_WINDOW", 0
        )
        process = subprocess.Popen(
            [sys.executable, "-m", "friday.app.sleep_display.app"],
            cwd=_PROJECT_ROOT,
            env={**os.environ, "FRIDAY_SLEEP_DISPLAY_CHILD": "1"},
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=creation_flags,
        )

        deadline = time.monotonic() + _startup_timeout()
        while time.monotonic() < deadline:
            state = _read_state()
            display_pid = int(state.get("pid") or 0)
            if display_pid and bool(state.get("ready")):
                return SleepDisplayResult(True, "start", display_pid, "Sleep display is ready.")
            if process.poll() is not None and not display_pid:
                return SleepDisplayResult(
                    False,
                    "start",
                    process.pid,
                    "Sleep display exited before its window became ready.",
                )
            time.sleep(0.1)

        state = _read_state()
        display_pid = int(state.get("pid") or process.pid)
        hwnd = _find_window(display_pid)
        if hwnd:
            ctypes.windll.user32.PostMessageW(hwnd, WM_CLOSE, 0, 0)
        _STATE_PATH.unlink(missing_ok=True)
        return SleepDisplayResult(False, "start", display_pid, "Sleep display startup timed out.")


def stop_sleep_display() -> SleepDisplayResult:
    if os.name != "nt":
        return SleepDisplayResult(False, "stop", 0, "Sleep display is available only on Windows.")

    with named_mutex("FRIDAY_SLEEP_DISPLAY_LIFECYCLE"):
        state = _read_state()
        pid = int(state.get("pid") or 0)
        hwnd = _find_window(pid) if pid else 0
        if not hwnd:
            hwnd = _find_window(0)
        if hwnd and not pid:
            pid = _window_process_id(hwnd)
        if not hwnd:
            _STATE_PATH.unlink(missing_ok=True)
            return SleepDisplayResult(True, "stop", pid, "No active sleep display window was found.")

        ctypes.windll.user32.PostMessageW(hwnd, WM_CLOSE, 0, 0)
        deadline = time.monotonic() + 5.0
        while time.monotonic() < deadline:
            if not _find_window(pid) and not _find_window(0):
                _STATE_PATH.unlink(missing_ok=True)
                return SleepDisplayResult(True, "stop", pid, "Sleep display closed.")
            time.sleep(0.1)
        return SleepDisplayResult(False, "stop", pid, "Sleep display did not close in time.")


def _read_state() -> dict:
    try:
        return json.loads(_STATE_PATH.read_text(encoding="utf-8"))
    except (OSError, TypeError, ValueError):
        return {}


def _find_window(pid: int) -> int:
    if os.name != "nt" or pid < 0:
        return 0
    user32 = ctypes.windll.user32
    handles: list[int] = []
    callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    @callback_type
    def callback(hwnd: int, _: int) -> bool:
        process_id = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(process_id))
        if pid and int(process_id.value) != pid:
            return True
        length = int(user32.GetWindowTextLengthW(hwnd))
        buffer = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buffer, len(buffer))
        if buffer.value.strip() == WINDOW_TITLE:
            handles.append(int(hwnd))
            return False
        return True

    user32.EnumWindows(callback, 0)
    return handles[0] if handles else 0


def _window_process_id(hwnd: int) -> int:
    if os.name != "nt" or not hwnd:
        return 0
    process_id = wintypes.DWORD()
    ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(process_id))
    return int(process_id.value)


def _enabled() -> bool:
    return os.getenv("FRIDAY_SLEEP_DISPLAY_ENABLED", "true").lower() in {"1", "true", "yes", "on"}


def _startup_timeout() -> float:
    try:
        return max(2.0, float(os.getenv("FRIDAY_SLEEP_DISPLAY_STARTUP_TIMEOUT", "10")))
    except ValueError:
        return 10.0
