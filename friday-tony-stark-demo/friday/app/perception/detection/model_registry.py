from __future__ import annotations

import os
from pathlib import Path

FRIDAY_DIR = Path(__file__).resolve().parents[3]
DEFAULT_MODEL_PATH = FRIDAY_DIR / "assets" / "models" / "vision" / "yolo26n.onnx"


def get_detection_model_path() -> Path:
    configured = os.getenv("FRIDAY_VISION_MODEL_PATH", "").strip()
    if not configured:
        return DEFAULT_MODEL_PATH
    path = Path(configured).expanduser()
    if not path.is_absolute():
        path = FRIDAY_DIR.parent / path
    return path.resolve()


def get_detection_confidence() -> float:
    raw_value = os.getenv("FRIDAY_VISION_CONFIDENCE", "0.35").strip()
    try:
        return min(0.95, max(0.05, float(raw_value)))
    except ValueError:
        return 0.35


def detection_enabled() -> bool:
    return os.getenv("FRIDAY_VISION_DETECTION_ENABLED", "true").lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def target_lock_enabled() -> bool:
    return os.getenv("FRIDAY_VISION_LOCK_ENABLED", "true").lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def get_target_lock_minimum_frames() -> int:
    raw_value = os.getenv("FRIDAY_VISION_LOCK_MIN_FRAMES", "2").strip()
    try:
        return min(12, max(1, int(raw_value)))
    except ValueError:
        return 2


def get_detection_target_fps(default: int) -> int:
    raw_value = os.getenv(
        "FRIDAY_VISION_DETECTOR_TARGET_FPS",
        os.getenv("FRIDAY_VISION_DETECTOR_FPS", str(default)),
    ).strip()
    try:
        return min(30, max(1, int(raw_value)))
    except ValueError:
        return default
