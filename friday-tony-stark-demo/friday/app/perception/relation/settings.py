from __future__ import annotations

import os


def relations_enabled() -> bool:
    value = os.getenv("FRIDAY_VISION_RELATIONS_ENABLED", "true")
    return value.strip().lower() in {"1", "true", "yes", "on"}


def get_hand_sample_fps(default: int = 6) -> int:
    try:
        value = int(os.getenv("FRIDAY_VISION_HAND_FPS", str(default)).strip())
    except ValueError:
        return default
    return min(15, max(1, value))
