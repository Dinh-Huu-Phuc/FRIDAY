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
BACKGROUND_WINDOW_TITLE = "FRIDAY Sleep Display Background"
WINDOW_TITLES = {WINDOW_TITLE, BACKGROUND_WINDOW_TITLE}
WM_CLOSE = 0x0010
SM_CMONITORS = 80
_FRIDAY_DIR = Path(__file__).resolve().parents[2]
_PROJECT_ROOT = _FRIDAY_DIR.parent
_STATE_PATH = _FRIDAY_DIR / "log" / "runtime" / "sleep_display.json"
_LOG_PATH = _FRIDAY_DIR / "log" / "runtime" / "sleep_display.log"


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
        if existing_pid and _state_is_ready(state) and _find_window(existing_pid):
            return SleepDisplayResult(True, "start", existing_pid, "Sleep display is already running.")
        _STATE_PATH.unlink(missing_ok=True)

        creation_flags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0) | getattr(
            subprocess, "CREATE_NO_WINDOW", 0
        )
        _LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        if _LOG_PATH.is_file() and _LOG_PATH.stat().st_size > 1_000_000:
            _LOG_PATH.unlink(missing_ok=True)
        with _LOG_PATH.open("ab") as child_log:
            process = subprocess.Popen(
                [sys.executable, "-m", "friday.app.sleep_display.app"],
                cwd=_PROJECT_ROOT,
                env={**os.environ, "FRIDAY_SLEEP_DISPLAY_CHILD": "1"},
                stdin=subprocess.DEVNULL,
                stdout=child_log,
                stderr=subprocess.STDOUT,
                creationflags=creation_flags,
            )

        deadline = time.monotonic() + _startup_timeout()
        while time.monotonic() < deadline:
            state = _read_state()
            display_pid = int(state.get("pid") or 0)
            child_is_alive = display_pid == process.pid and process.poll() is None
            if display_pid and _state_is_ready(state) and (
                child_is_alive or _find_window(display_pid)
            ):
                return SleepDisplayResult(True, "start", display_pid, "Sleep display is ready.")
            if process.poll() is not None and not display_pid:
                return SleepDisplayResult(
                    False,
                    "start",
                    process.pid,
                    "Sleep display exited before its window became ready.",
                )
            time.sleep(0.02)

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
        deadline = time.monotonic() + 0.75
        while time.monotonic() < deadline:
            if not _find_window(pid) and not _find_window(0):
                _STATE_PATH.unlink(missing_ok=True)
                return SleepDisplayResult(True, "stop", pid, "Sleep display closed.")
            time.sleep(0.05)
        if _terminate_process(pid):
            _STATE_PATH.unlink(missing_ok=True)
            return SleepDisplayResult(True, "stop", pid, "Sleep display closed.")
        return SleepDisplayResult(False, "stop", pid, "Sleep display did not close in time.")


def _read_state() -> dict:
    try:
        return json.loads(_STATE_PATH.read_text(encoding="utf-8"))
    except (OSError, TypeError, ValueError):
        return {}


def _state_is_ready(state: dict) -> bool:
    try:
        screen_count = int(state.get("screen_count") or 0)
    except (TypeError, ValueError):
        return False
    return bool(state.get("ready")) and screen_count >= _expected_screen_count()


def _expected_screen_count() -> int:
    if os.name != "nt":
        return 1
    try:
        return max(1, int(ctypes.windll.user32.GetSystemMetrics(SM_CMONITORS)))
    except (AttributeError, OSError, TypeError, ValueError):
        return 1


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
        if buffer.value.strip() in WINDOW_TITLES:
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


def _terminate_process(pid: int) -> bool:
    if os.name != "nt" or pid <= 0 or pid == os.getpid():
        return False
    kernel32 = ctypes.windll.kernel32
    kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel32.OpenProcess.restype = wintypes.HANDLE
    kernel32.TerminateProcess.argtypes = [wintypes.HANDLE, wintypes.UINT]
    kernel32.TerminateProcess.restype = wintypes.BOOL
    kernel32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    process_handle = kernel32.OpenProcess(0x0001 | 0x00100000, False, pid)
    if not process_handle:
        return not bool(_find_window(pid))
    try:
        terminated = bool(kernel32.TerminateProcess(process_handle, 0))
        if terminated:
            kernel32.WaitForSingleObject(process_handle, 1_000)
        return terminated
    finally:
        kernel32.CloseHandle(process_handle)


def _enabled() -> bool:
    return os.getenv("FRIDAY_SLEEP_DISPLAY_ENABLED", "true").lower() in {"1", "true", "yes", "on"}


def _startup_timeout() -> float:
    try:
        return max(1.0, float(os.getenv("FRIDAY_SLEEP_DISPLAY_STARTUP_TIMEOUT", "4")))
    except ValueError:
        return 4.0
