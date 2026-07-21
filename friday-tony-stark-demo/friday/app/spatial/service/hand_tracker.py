from __future__ import annotations

from typing import Any

from friday.app.spatial.exceptions import VisionDependencyError
from friday.app.spatial.service.coordinate_mapper import CoordinateMapper


class HandTracker:
    def __init__(self, mapper: CoordinateMapper | None = None) -> None:
        self._mapper = mapper or CoordinateMapper()
        self._hands: Any | None = None
        self._cv2: Any | None = None
        self._mp_hands: Any | None = None

    def _ensure_tracker(self) -> None:
        if self._hands is not None:
            return
        try:
            import cv2  # type: ignore
            import mediapipe as mp  # type: ignore
        except ImportError as exc:
            raise VisionDependencyError("mediapipe and opencv-python are required for hand tracking.") from exc
        self._cv2 = cv2
        self._mp_hands = mp.solutions.hands
        self._hands = self._mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=2,
            model_complexity=1,
            min_detection_confidence=0.55,
            min_tracking_confidence=0.55,
        )

    def detect(self, frame) -> list[dict[str, Any]]:
        self._ensure_tracker()
        rgb = self._cv2.cvtColor(frame, self._cv2.COLOR_BGR2RGB)
        result = self._hands.process(rgb)
        if not result.multi_hand_landmarks:
            return []

        hands: list[dict[str, Any]] = []
        handedness = result.multi_handedness or []
        for index, hand_landmarks in enumerate(result.multi_hand_landmarks):
            label = "unknown"
            score = 0.0
            if index < len(handedness):
                classification = handedness[index].classification[0]
                label = str(classification.label).lower()
                score = float(classification.score)
            points = self._mapper.normalize_landmarks(hand_landmarks.landmark)
            hands.append({"hand": label, "hand_confidence": score, "points": points})
        return hands

    def close(self) -> None:
        if self._hands is not None:
            self._hands.close()
            self._hands = None
