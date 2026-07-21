"""Pure geometry helpers for the capture border animation."""

from __future__ import annotations


Point = tuple[float, float]


def perimeter_length(width: float, height: float, *, inset: float = 5.0) -> float:
    inner_width = max(1.0, float(width) - (2.0 * inset))
    inner_height = max(1.0, float(height) - (2.0 * inset))
    return 2.0 * (inner_width + inner_height)


def point_on_perimeter(
    distance: float,
    width: float,
    height: float,
    *,
    inset: float = 5.0,
) -> Point:
    inner_width = max(1.0, float(width) - (2.0 * inset))
    inner_height = max(1.0, float(height) - (2.0 * inset))
    perimeter = 2.0 * (inner_width + inner_height)
    position = float(distance) % perimeter

    if position <= inner_width:
        return inset + position, inset
    position -= inner_width
    if position <= inner_height:
        return inset + inner_width, inset + position
    position -= inner_height
    if position <= inner_width:
        return inset + inner_width - position, inset + inner_height
    position -= inner_width
    return inset, inset + inner_height - position


def trail_points(
    *,
    head_distance: float,
    direction: int,
    width: float,
    height: float,
    tail_fraction: float = 0.17,
    segments: int = 44,
    inset: float = 5.0,
) -> list[Point]:
    direction = 1 if direction >= 0 else -1
    segment_count = max(2, int(segments))
    perimeter = perimeter_length(width, height, inset=inset)
    tail_length = perimeter * max(0.02, min(float(tail_fraction), 0.45))
    return [
        point_on_perimeter(
            head_distance - direction * tail_length * (1.0 - index / segment_count),
            width,
            height,
            inset=inset,
        )
        for index in range(segment_count + 1)
    ]
