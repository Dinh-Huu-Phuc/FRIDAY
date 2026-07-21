from __future__ import annotations

from friday.app.spatial.constants import DEFAULT_GESTURE_MAPPING


def action_for_gesture(gesture: str) -> str | None:
    return DEFAULT_GESTURE_MAPPING.get(gesture)


def gesture_mapping() -> dict[str, str]:
    return dict(DEFAULT_GESTURE_MAPPING)
