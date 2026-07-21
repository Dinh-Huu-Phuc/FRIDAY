from __future__ import annotations

from friday.core.schemas.spatial_entities import SpatialPosition


class CoordinateMapper:
    def normalize_landmarks(self, landmarks) -> dict[int, tuple[float, float, float]]:
        return {
            index: (
                max(0.0, min(1.0, float(point.x))),
                max(0.0, min(1.0, float(point.y))),
                float(point.z),
            )
            for index, point in enumerate(landmarks)
        }

    def palm_position(self, points: dict[int, tuple[float, float, float]]) -> SpatialPosition:
        wrist = points.get(0, (0.5, 0.5, 0.0))
        return SpatialPosition(x=wrist[0], y=wrist[1], z=wrist[2])
