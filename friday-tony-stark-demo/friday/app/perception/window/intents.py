from __future__ import annotations

import re

from friday.app.perception.window.schemas import (
    CameraWindowAction,
    CameraWindowIntentMatch,
)

_PHRASES = {
    "open camera": (CameraWindowAction.OPEN, "open_camera"),
    "friday open camera": (CameraWindowAction.OPEN, "friday_open_camera"),
    "show camera": (CameraWindowAction.OPEN, "show_camera"),
    "friday show camera": (CameraWindowAction.OPEN, "friday_show_camera"),
    "open webcam": (CameraWindowAction.OPEN, "open_webcam"),
    "friday open webcam": (CameraWindowAction.OPEN, "friday_open_webcam"),
    "show webcam": (CameraWindowAction.OPEN, "show_webcam"),
    "launch camera": (CameraWindowAction.OPEN, "launch_camera"),
    "friday launch camera": (CameraWindowAction.OPEN, "friday_launch_camera"),
    "open camera window": (CameraWindowAction.OPEN, "open_camera_window"),
    "friday open camera window": (CameraWindowAction.OPEN, "friday_open_camera_window"),
    "close camera": (CameraWindowAction.CLOSE, "close_camera"),
    "friday close camera": (CameraWindowAction.CLOSE, "friday_close_camera"),
    "hide camera": (CameraWindowAction.CLOSE, "hide_camera"),
    "friday hide camera": (CameraWindowAction.CLOSE, "friday_hide_camera"),
    "close webcam": (CameraWindowAction.CLOSE, "close_webcam"),
    "friday close webcam": (CameraWindowAction.CLOSE, "friday_close_webcam"),
    "close camera window": (CameraWindowAction.CLOSE, "close_camera_window"),
    "friday close camera window": (CameraWindowAction.CLOSE, "friday_close_camera_window"),
    "analyze camera": (CameraWindowAction.ANALYZE, "analyze_camera"),
    "friday analyze camera": (CameraWindowAction.ANALYZE, "friday_analyze_camera"),
    "what do you see through camera": (
        CameraWindowAction.ANALYZE,
        "describe_camera_scene",
    ),
    "friday what do you see through camera": (
        CameraWindowAction.ANALYZE,
        "friday_describe_camera_scene",
    ),
    "what can you see through camera": (
        CameraWindowAction.ANALYZE,
        "describe_camera_scene_alternative",
    ),
}


def normalize_camera_window_phrase(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", " ", str(value or "").lower()).strip()
    normalized = re.sub(r"^friday\s+agent\b", "friday", normalized)
    normalized = re.sub(r"\bthe\s+(?=camera|webcam)", "", normalized)
    return re.sub(r"\s+", " ", normalized).strip()


def match_camera_window_intent(message: str) -> CameraWindowIntentMatch:
    matched = _PHRASES.get(normalize_camera_window_phrase(message))
    if matched is None:
        return CameraWindowIntentMatch()
    action, trigger_id = matched
    return CameraWindowIntentMatch(action=action, trigger_id=trigger_id)
