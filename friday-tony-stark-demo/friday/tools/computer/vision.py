"""Screen capture and screen metadata helpers."""

from __future__ import annotations

import ctypes
from pathlib import Path
from typing import Any

from ctypes import wintypes


MONITOR_DEFAULTTONEAREST = 2
DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2 = -4


class MONITORINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("rcMonitor", wintypes.RECT),
        ("rcWork", wintypes.RECT),
        ("dwFlags", wintypes.DWORD),
    ]


def _enable_per_monitor_dpi_awareness() -> None:
    if not hasattr(ctypes, "windll"):
        return
    try:
        setter = ctypes.windll.user32.SetProcessDpiAwarenessContext
        setter.argtypes = [ctypes.c_void_p]
        setter.restype = wintypes.BOOL
        setter(ctypes.c_void_p(DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2))
    except (AttributeError, OSError):
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except (AttributeError, OSError):
            return


_enable_per_monitor_dpi_awareness()


def _get_image_grab():
    try:
        from PIL import ImageGrab
    except Exception as exc:
        raise RuntimeError(
            "Pillow ImageGrab is required for screenshots. Install it with `uv add pillow`."
        ) from exc
    return ImageGrab


def get_active_window_title() -> str:
    try:
        user32 = ctypes.windll.user32
        handle = user32.GetForegroundWindow()
        if not handle:
            return ""
        length = user32.GetWindowTextLengthW(handle)
        if length <= 0:
            return ""
        buffer = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(handle, buffer, length + 1)
        return buffer.value.strip()
    except Exception:
        return ""


def get_screen_size() -> dict[str, int]:
    try:
        from friday.tools.computer import get_pyautogui

        pyautogui = get_pyautogui()
        width, height = pyautogui.size()
        return {"width": int(width), "height": int(height)}
    except Exception:
        image = _get_image_grab().grab(all_screens=True)
        width, height = image.size
        return {"width": int(width), "height": int(height)}


def get_monitors() -> list[dict[str, int | bool]]:
    if not hasattr(ctypes, "windll"):
        size = get_screen_size()
        return [
            {
                "index": 1,
                "handle": 0,
                "left": 0,
                "top": 0,
                "right": size["width"],
                "bottom": size["height"],
                "width": size["width"],
                "height": size["height"],
                "is_primary": True,
            }
        ]

    user32 = ctypes.windll.user32
    monitors: list[dict[str, int | bool]] = []
    callback_type = ctypes.WINFUNCTYPE(
        wintypes.BOOL,
        wintypes.HMONITOR,
        wintypes.HDC,
        ctypes.POINTER(wintypes.RECT),
        wintypes.LPARAM,
    )
    user32.GetMonitorInfoW.argtypes = [wintypes.HMONITOR, ctypes.POINTER(MONITORINFO)]
    user32.GetMonitorInfoW.restype = wintypes.BOOL

    @callback_type
    def callback(monitor_handle, _device_context, _rect, _data):
        info = MONITORINFO()
        info.cbSize = ctypes.sizeof(MONITORINFO)
        if user32.GetMonitorInfoW(monitor_handle, ctypes.byref(info)):
            rect = info.rcMonitor
            monitors.append(
                {
                    "handle": int(monitor_handle),
                    "left": int(rect.left),
                    "top": int(rect.top),
                    "right": int(rect.right),
                    "bottom": int(rect.bottom),
                    "width": int(rect.right - rect.left),
                    "height": int(rect.bottom - rect.top),
                    "is_primary": bool(info.dwFlags & 1),
                }
            )
        return True

    user32.EnumDisplayMonitors(None, None, callback, 0)
    monitors.sort(
        key=lambda item: (
            not bool(item["is_primary"]),
            int(item["left"]),
            int(item["top"]),
        )
    )
    for index, monitor in enumerate(monitors, start=1):
        monitor["index"] = index
    return monitors


def get_active_monitor() -> dict[str, int | bool]:
    monitors = get_monitors()
    if not monitors or not hasattr(ctypes, "windll"):
        return monitors[0]

    user32 = ctypes.windll.user32
    user32.GetForegroundWindow.restype = wintypes.HWND
    user32.MonitorFromWindow.argtypes = [wintypes.HWND, wintypes.DWORD]
    user32.MonitorFromWindow.restype = wintypes.HMONITOR
    handle = int(
        user32.MonitorFromWindow(
            user32.GetForegroundWindow(),
            MONITOR_DEFAULTTONEAREST,
        )
        or 0
    )
    return next(
        (monitor for monitor in monitors if int(monitor["handle"]) == handle),
        monitors[0],
    )


def capture_screen(output_path: str | Path) -> dict[str, Any]:
    target_path = Path(output_path).expanduser().resolve()
    target_path.parent.mkdir(parents=True, exist_ok=True)
    image = _get_image_grab().grab(all_screens=True)
    image.save(target_path)
    width, height = image.size
    return {
        "path": str(target_path),
        "screen_width": int(width),
        "screen_height": int(height),
        "active_window_title": get_active_window_title(),
    }


def capture_monitor(
    output_path: str | Path,
    monitor: dict[str, int | bool],
) -> dict[str, Any]:
    target_path = Path(output_path).expanduser().resolve()
    target_path.parent.mkdir(parents=True, exist_ok=True)
    bounds = (
        int(monitor["left"]),
        int(monitor["top"]),
        int(monitor["right"]),
        int(monitor["bottom"]),
    )
    image = _get_image_grab().grab(bbox=bounds, all_screens=True)
    image.save(target_path)
    return {
        "path": str(target_path),
        "screen_width": int(image.width),
        "screen_height": int(image.height),
        "active_window_title": get_active_window_title(),
    }


def compress_image(
    source_path: str | Path,
    target_path: str | Path | None = None,
    *,
    quality: int = 70,
    max_width: int = 1600,
    max_height: int = 900,
) -> str:
    from PIL import Image

    source = Path(source_path).expanduser().resolve()
    destination = (
        Path(target_path).expanduser().resolve()
        if target_path is not None
        else source.with_name(f"{source.stem}_compressed.jpg")
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(source) as image:
        image = image.convert("RGB")
        image.thumbnail((int(max_width), int(max_height)))
        image.save(
            destination,
            format="JPEG",
            quality=int(quality),
            optimize=True,
            subsampling=0,
        )
    return str(destination)
