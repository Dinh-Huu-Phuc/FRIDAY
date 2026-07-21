from __future__ import annotations


def _is_folded(points: dict[int, tuple[float, float, float]], tip: int, pip: int) -> bool:
    tip_point = points.get(tip)
    pip_point = points.get(pip)
    if tip_point is None or pip_point is None:
        return False
    return tip_point[1] > pip_point[1]


def detect_grab(points: dict[int, tuple[float, float, float]]) -> tuple[bool, float]:
    folded = [
        _is_folded(points, 8, 6),
        _is_folded(points, 12, 10),
        _is_folded(points, 16, 14),
        _is_folded(points, 20, 18),
    ]
    score = sum(1 for value in folded if value) / 4
    return score >= 0.75, score
