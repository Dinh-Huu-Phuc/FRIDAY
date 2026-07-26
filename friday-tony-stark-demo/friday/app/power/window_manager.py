"""Snapshot, minimize, and restore visible Windows application windows."""

from __future__ import annotations

import ctypes
import json
import os
import threading
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Protocol
from uuid import uuid4

from ctypes import wintypes


SW_MINIMIZE = 6
GWL_EXSTYLE = -20
WS_EX_TOOLWINDOW = 0x00000080
GA_ROOT = 2
SHELL_WINDOW_CLASSES = {"Progman", "WorkerW", "Shell_TrayWnd", "Shell_SecondaryTrayWnd"}
SLEEP_DISPLAY_WINDOW_TITLES = {"FRIDAY Sleep Display", "FRIDAY Sleep Display Background"}

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_DEFAULT_SNAPSHOT_PATH = _PROJECT_ROOT / "friday" / "log" / "runtime" / "window_sleep_session.json"
_LOCK = threading.RLock()


class WINDOWPLACEMENT(ctypes.Structure):
    _fields_ = [
        ("length", wintypes.UINT),
        ("flags", wintypes.UINT),
        ("showCmd", wintypes.UINT),
        ("ptMinPosition", wintypes.POINT),
        ("ptMaxPosition", wintypes.POINT),
        ("rcNormalPosition", wintypes.RECT),
    ]


@dataclass(frozen=True, slots=True)
class WindowRecord:
    hwnd: int
    pid: int
    title: str
    class_name: str
    placement: dict[str, Any]


@dataclass(frozen=True, slots=True)
class WindowActionResult:
    ok: bool
    action: str
    affected: int
    skipped: int
    message: str

    def to_dict(self) -> dict[str, str | int | bool]:
        return asdict(self)


class WindowBackend(Protocol):
    def list_windows(self) -> list[int]: ...
    def is_candidate(self, hwnd: int) -> bool: ...
    def capture(self, hwnd: int) -> WindowRecord | None: ...
    def minimize(self, hwnd: int) -> bool: ...
    def is_same_window(self, record: WindowRecord) -> bool: ...
    def restore(self, record: WindowRecord) -> bool: ...


def _point_to_dict(point: wintypes.POINT) -> dict[str, int]:
    return {"x": int(point.x), "y": int(point.y)}


def _rect_to_dict(rect: wintypes.RECT) -> dict[str, int]:
    return {
        "left": int(rect.left),
        "top": int(rect.top),
        "right": int(rect.right),
        "bottom": int(rect.bottom),
    }


def _placement_to_dict(placement: WINDOWPLACEMENT) -> dict[str, Any]:
    return {
        "flags": int(placement.flags),
        "show_cmd": int(placement.showCmd),
        "min_position": _point_to_dict(placement.ptMinPosition),
        "max_position": _point_to_dict(placement.ptMaxPosition),
        "normal_position": _rect_to_dict(placement.rcNormalPosition),
    }


def _dict_to_placement(payload: dict[str, Any]) -> WINDOWPLACEMENT:
    placement = WINDOWPLACEMENT()
    placement.length = ctypes.sizeof(WINDOWPLACEMENT)
    placement.flags = int(payload.get("flags") or 0)
    placement.showCmd = int(payload.get("show_cmd") or 1)
    minimum = payload.get("min_position") or {}
    maximum = payload.get("max_position") or {}
    normal = payload.get("normal_position") or {}
    placement.ptMinPosition = wintypes.POINT(int(minimum.get("x") or 0), int(minimum.get("y") or 0))
    placement.ptMaxPosition = wintypes.POINT(int(maximum.get("x") or 0), int(maximum.get("y") or 0))
    placement.rcNormalPosition = wintypes.RECT(
        int(normal.get("left") or 0),
        int(normal.get("top") or 0),
        int(normal.get("right") or 0),
        int(normal.get("bottom") or 0),
    )
    return placement


class Win32WindowBackend:
    def __init__(self) -> None:
        if os.name != "nt":
            raise RuntimeError("Window sleep is available only on Windows")
        self.user32 = ctypes.windll.user32
        self._get_window_long = getattr(self.user32, "GetWindowLongPtrW", self.user32.GetWindowLongW)
        self._configure_api()

    def _configure_api(self) -> None:
        self.user32.IsWindow.argtypes = [wintypes.HWND]
        self.user32.IsWindow.restype = wintypes.BOOL
        self.user32.IsWindowVisible.argtypes = [wintypes.HWND]
        self.user32.IsWindowVisible.restype = wintypes.BOOL
        self.user32.IsIconic.argtypes = [wintypes.HWND]
        self.user32.IsIconic.restype = wintypes.BOOL
        self.user32.GetAncestor.argtypes = [wintypes.HWND, wintypes.UINT]
        self.user32.GetAncestor.restype = wintypes.HWND
        self.user32.GetShellWindow.restype = wintypes.HWND
        self.user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
        self.user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
        self.user32.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
        self.user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
        self.user32.GetWindowPlacement.argtypes = [wintypes.HWND, ctypes.POINTER(WINDOWPLACEMENT)]
        self.user32.SetWindowPlacement.argtypes = [wintypes.HWND, ctypes.POINTER(WINDOWPLACEMENT)]
        self.user32.ShowWindowAsync.argtypes = [wintypes.HWND, ctypes.c_int]
        self.user32.ShowWindowAsync.restype = wintypes.BOOL
        self._get_window_long.argtypes = [wintypes.HWND, ctypes.c_int]
        self._get_window_long.restype = ctypes.c_ssize_t
        self._configure_api()

    def _configure_api(self) -> None:
        self.user32.IsWindow.argtypes = [wintypes.HWND]
        self.user32.IsWindow.restype = wintypes.BOOL
        self.user32.IsWindowVisible.argtypes = [wintypes.HWND]
        self.user32.IsWindowVisible.restype = wintypes.BOOL
        self.user32.IsIconic.argtypes = [wintypes.HWND]
        self.user32.IsIconic.restype = wintypes.BOOL
        self.user32.GetAncestor.argtypes = [wintypes.HWND, wintypes.UINT]
        self.user32.GetAncestor.restype = wintypes.HWND
        self.user32.GetShellWindow.restype = wintypes.HWND
        self.user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
        self.user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
        self.user32.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
        self.user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
        self.user32.GetWindowPlacement.argtypes = [wintypes.HWND, ctypes.POINTER(WINDOWPLACEMENT)]
        self.user32.SetWindowPlacement.argtypes = [wintypes.HWND, ctypes.POINTER(WINDOWPLACEMENT)]
        self.user32.ShowWindowAsync.argtypes = [wintypes.HWND, ctypes.c_int]
        self.user32.ShowWindowAsync.restype = wintypes.BOOL
        self._get_window_long.argtypes = [wintypes.HWND, ctypes.c_int]
        self._get_window_long.restype = ctypes.c_ssize_t

    def list_windows(self) -> list[int]:
        handles: list[int] = []
        callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

        @callback_type
        def callback(hwnd: int, _: int) -> bool:
            handles.append(int(hwnd))
            return True

        self.user32.EnumWindows(callback, 0)
        return handles

    def _text(self, hwnd: int) -> str:
        length = int(self.user32.GetWindowTextLengthW(hwnd))
        if length <= 0:
            return ""
        buffer = ctypes.create_unicode_buffer(length + 1)
        self.user32.GetWindowTextW(hwnd, buffer, len(buffer))
        return buffer.value.strip()

    def _class_name(self, hwnd: int) -> str:
        buffer = ctypes.create_unicode_buffer(256)
        self.user32.GetClassNameW(hwnd, buffer, len(buffer))
        return buffer.value.strip()

    def _pid(self, hwnd: int) -> int:
        pid = wintypes.DWORD()
        self.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        return int(pid.value)

    def is_candidate(self, hwnd: int) -> bool:
        if not self.user32.IsWindow(hwnd) or not self.user32.IsWindowVisible(hwnd):
            return False
        if self.user32.IsIconic(hwnd) or int(self.user32.GetAncestor(hwnd, GA_ROOT)) != int(hwnd):
            return False
        if int(hwnd) == int(self.user32.GetShellWindow()):
            return False
        if self._class_name(hwnd) in SHELL_WINDOW_CLASSES:
            return False
        if int(self._get_window_long(hwnd, GWL_EXSTYLE)) & WS_EX_TOOLWINDOW:
            return False
        title = self._text(hwnd)
        return bool(title) and title not in SLEEP_DISPLAY_WINDOW_TITLES

    def capture(self, hwnd: int) -> WindowRecord | None:
        placement = WINDOWPLACEMENT()
        placement.length = ctypes.sizeof(WINDOWPLACEMENT)
        if not self.user32.GetWindowPlacement(hwnd, ctypes.byref(placement)):
            return None
        return WindowRecord(
            hwnd=int(hwnd),
            pid=self._pid(hwnd),
            title=self._text(hwnd),
            class_name=self._class_name(hwnd),
            placement=_placement_to_dict(placement),
        )

    def minimize(self, hwnd: int) -> bool:
        return bool(self.user32.ShowWindowAsync(hwnd, SW_MINIMIZE))

    def is_same_window(self, record: WindowRecord) -> bool:
        return bool(self.user32.IsWindow(record.hwnd)) and self._pid(record.hwnd) == record.pid

    def restore(self, record: WindowRecord) -> bool:
        placement = _dict_to_placement(record.placement)
        return bool(self.user32.SetWindowPlacement(record.hwnd, ctypes.byref(placement)))


class WindowSleepManager:
    def __init__(
        self,
        *,
        backend: WindowBackend | None = None,
        snapshot_path: Path | None = None,
        transition_delay_seconds: float | None = None,
    ) -> None:
        self.backend = backend
        self.snapshot_path = snapshot_path or _snapshot_path()
        self.transition_delay_seconds = (
            _transition_delay_seconds()
            if transition_delay_seconds is None
            else max(0.0, transition_delay_seconds)
        )

    def _pause_between_windows(self, index: int, total: int) -> None:
        if self.transition_delay_seconds > 0 and index < total - 1:
            time.sleep(self.transition_delay_seconds)

    def _active_backend(self) -> WindowBackend | None:
        if self.backend is not None:
            return self.backend
        if os.name != "nt":
            return None
        return Win32WindowBackend()

    def _save(self, records: list[WindowRecord]) -> None:
        self.snapshot_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.snapshot_path.with_name(f".{self.snapshot_path.name}.{uuid4().hex}.tmp")
        temporary.write_text(
            json.dumps({"active": True, "windows": [asdict(record) for record in records]}, indent=2),
            encoding="utf-8",
        )
        temporary.replace(self.snapshot_path)

    def _load(self) -> list[WindowRecord]:
        if not self.snapshot_path.is_file():
            return []
        try:
            payload = json.loads(self.snapshot_path.read_text(encoding="utf-8"))
            return [WindowRecord(**item) for item in payload.get("windows", [])]
        except (OSError, TypeError, ValueError):
            return []

    def minimize_all(self) -> WindowActionResult:
        backend = self._active_backend()
        if backend is None:
            return WindowActionResult(False, "minimize", 0, 0, "Window sleep is available only on Windows.")

        with _LOCK:
            existing_records = self._load()
            records: list[WindowRecord] = []
            skipped = 0
            for hwnd in backend.list_windows():
                if not backend.is_candidate(hwnd):
                    skipped += 1
                    continue
                record = backend.capture(hwnd)
                if record is not None:
                    records.append(record)

            merged = {(record.hwnd, record.pid): record for record in existing_records}
            merged.update({(record.hwnd, record.pid): record for record in records})
            self._save(list(merged.values()))
            affected = 0
            for index, record in enumerate(records):
                if backend.minimize(record.hwnd):
                    affected += 1
                else:
                    skipped += 1
                self._pause_between_windows(index, len(records))
            return WindowActionResult(True, "minimize", affected, skipped, f"Minimized {affected} windows.")

    def restore_all(self) -> WindowActionResult:
        backend = self._active_backend()
        if backend is None:
            return WindowActionResult(False, "restore", 0, 0, "Window restore is available only on Windows.")

        with _LOCK:
            records = self._load()
            affected = 0
            skipped = 0
            restore_records = list(reversed(records))
            for index, record in enumerate(restore_records):
                if not backend.is_same_window(record):
                    skipped += 1
                    self._pause_between_windows(index, len(restore_records))
                    continue
                if backend.restore(record):
                    affected += 1
                else:
                    skipped += 1
                self._pause_between_windows(index, len(restore_records))
            if self.snapshot_path.is_file():
                self.snapshot_path.unlink()
            return WindowActionResult(True, "restore", affected, skipped, f"Restored {affected} windows.")


def _snapshot_path() -> Path:
    configured = os.getenv("FRIDAY_WINDOW_SNAPSHOT_PATH", "").strip()
    return Path(configured).expanduser().resolve() if configured else _DEFAULT_SNAPSHOT_PATH


def _transition_delay_seconds() -> float:
    try:
        milliseconds = float(os.getenv("FRIDAY_WINDOW_TRANSITION_DELAY_MS", "0"))
    except ValueError:
        milliseconds = 0.0
    return min(max(milliseconds, 0.0), 2_000.0) / 1_000.0


def window_sleep_enabled() -> bool:
    return os.getenv("FRIDAY_WINDOW_SLEEP_ENABLED", "true").lower() in {"1", "true", "yes", "on"}


def minimize_application_windows() -> WindowActionResult:
    if not window_sleep_enabled():
        return WindowActionResult(False, "minimize", 0, 0, "Window sleep is disabled.")
    return WindowSleepManager().minimize_all()


def restore_application_windows() -> WindowActionResult:
    if not window_sleep_enabled():
        return WindowActionResult(False, "restore", 0, 0, "Window restore is disabled.")
    return WindowSleepManager().restore_all()
