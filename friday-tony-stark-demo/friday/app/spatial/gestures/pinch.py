from __future__ import annotations

from math import dist


def detect_pinch(points: dict[int, tuple[float, float, float]]) -> tuple[bool, float]:
    thumb_tip = points.get(4)
    index_tip = points.get(8)
    if thumb_tip is None or index_tip is None:
        return False, 0.0
    distance = dist(thumb_tip[:2], index_tip[:2])
    confidence = max(0.0, min(1.0, 1.0 - distance / 0.12))
    return distance < 0.055, confidence
