from __future__ import annotations

from friday.app.spatial.constants import GESTURE_GRAB, GESTURE_IDLE, GESTURE_OPEN_PALM, GESTURE_PINCH
from friday.app.spatial.gestures.grab import detect_grab
from friday.app.spatial.gestures.open_palm import detect_open_palm
from friday.app.spatial.gestures.pinch import detect_pinch
from friday.core.schemas.spatial_entities import FingerState


class GestureEngine:
    def classify(self, points: dict[int, tuple[float, float, float]]) -> tuple[str, float, FingerState]:
        fingers = self._finger_state(points)
        pinch, pinch_confidence = detect_pinch(points)
        if pinch:
            return GESTURE_PINCH, pinch_confidence, fingers

        grab, grab_confidence = detect_grab(points)
        if grab:
            return GESTURE_GRAB, grab_confidence, fingers

        open_palm, open_confidence = detect_open_palm(points)
        if open_palm:
            return GESTURE_OPEN_PALM, open_confidence, fingers

        return GESTURE_IDLE, 0.0, fingers

    def _finger_state(self, points: dict[int, tuple[float, float, float]]) -> FingerState:
        return FingerState(
            thumb=self._thumb_extended(points),
            index=self._extended(points, 8, 6),
            middle=self._extended(points, 12, 10),
            ring=self._extended(points, 16, 14),
            pinky=self._extended(points, 20, 18),
        )

    def _extended(self, points: dict[int, tuple[float, float, float]], tip: int, pip: int) -> bool:
        tip_point = points.get(tip)
        pip_point = points.get(pip)
        return bool(tip_point and pip_point and tip_point[1] < pip_point[1])

    def _thumb_extended(self, points: dict[int, tuple[float, float, float]]) -> bool:
        tip = points.get(4)
        ip = points.get(3)
        return bool(tip and ip and abs(tip[0] - ip[0]) > 0.035)
