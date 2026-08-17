from __future__ import annotations

import os

DEFAULT_CAMERA_INDEX = 0
DEFAULT_CAMERA_RENDER_FPS = 60
DEFAULT_HUD_SMOOTHING_MS = 110


def get_default_camera_index() -> int:
    raw_value = os.getenv("FRIDAY_CAMERA_INDEX", str(DEFAULT_CAMERA_INDEX)).strip()
    try:
        camera_index = int(raw_value)
    except ValueError:
        return DEFAULT_CAMERA_INDEX
    return camera_index if camera_index >= 0 else DEFAULT_CAMERA_INDEX


def get_camera_render_fps() -> int:
    raw_value = os.getenv(
        "FRIDAY_CAMERA_RENDER_FPS",
        str(DEFAULT_CAMERA_RENDER_FPS),
    ).strip()
    try:
        return min(120, max(24, int(raw_value)))
    except ValueError:
        return DEFAULT_CAMERA_RENDER_FPS


def get_hud_smoothing_ms() -> int:
    raw_value = os.getenv(
        "FRIDAY_CAMERA_HUD_SMOOTHING_MS",
        str(DEFAULT_HUD_SMOOTHING_MS),
    ).strip()
    try:
        return min(350, max(40, int(raw_value)))
    except ValueError:
        return DEFAULT_HUD_SMOOTHING_MS
