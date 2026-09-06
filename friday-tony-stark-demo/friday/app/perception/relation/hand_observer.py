from __future__ import annotations

from typing import Any

from friday.app.perception.scene.schemas import HandObservation
from friday.app.spatial.constants import GESTURE_GRAB, GESTURE_PINCH
from friday.app.spatial.service.gesture_engine import GestureEngine
from friday.app.spatial.service.hand_tracker import HandTracker


class HandObservationProvider:
    """Convert MediaPipe hand landmarks into relation-friendly observations."""

    def __init__(
        self,
        tracker: HandTracker | None = None,
        gesture_engine: GestureEngine | None = None,
    ) -> None:
        self._tracker = tracker or HandTracker()
        self._gestures = gesture_engine or GestureEngine()

    def detect(self, frame: Any) -> tuple[HandObservation, ...]:
        observations: list[HandObservation] = []
        handedness_counts: dict[str, int] = {}
        for raw_hand in self._tracker.detect(frame):
            points = raw_hand.get("points") or {}
            handedness = str(raw_hand.get("hand") or "unknown").lower()
            handedness_counts[handedness] = handedness_counts.get(handedness, 0) + 1
            hand_id = f"{handedness}-{handedness_counts[handedness]}"
            gesture, gesture_confidence, fingers = self._gestures.classify(points)
            hand_confidence = float(raw_hand.get("hand_confidence") or 0.0)
            thumb_tip = _point(points, 4)
            index_base = _point(points, 5)
            index_tip = _point(points, 8)
            palm = _point(points, 9, fallback=_point(points, 0))
            interaction_x = (thumb_tip[0] + index_tip[0]) / 2
            interaction_y = (thumb_tip[1] + index_tip[1]) / 2
            is_gripping = gesture in {GESTURE_GRAB, GESTURE_PINCH}
            is_pointing = (
                fingers.index
                and not fingers.middle
                and not fingers.ring
                and not fingers.pinky
                and not is_gripping
            )
            observations.append(
                HandObservation(
                    hand_id=hand_id,
                    handedness=handedness,
                    confidence=min(1.0, max(hand_confidence, gesture_confidence)),
                    gesture=gesture,
                    is_pointing=is_pointing,
                    is_gripping=is_gripping,
                    palm_x=palm[0],
                    palm_y=palm[1],
                    interaction_x=interaction_x,
                    interaction_y=interaction_y,
                    index_base_x=index_base[0],
                    index_base_y=index_base[1],
                    index_tip_x=index_tip[0],
                    index_tip_y=index_tip[1],
                )
            )
        return tuple(observations)

    def close(self) -> None:
        self._tracker.close()


def _point(
    points: dict[int, tuple[float, float, float]],
    index: int,
    *,
    fallback: tuple[float, float] = (0.5, 0.5),
) -> tuple[float, float]:
    point = points.get(index)
    if point is None:
        return fallback
    return (
        min(1.0, max(0.0, float(point[0]))),
        min(1.0, max(0.0, float(point[1]))),
    )
