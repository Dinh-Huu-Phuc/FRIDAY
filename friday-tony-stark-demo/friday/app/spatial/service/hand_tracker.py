from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any

from friday.app.spatial.exceptions import VisionDependencyError
from friday.app.spatial.service.coordinate_mapper import CoordinateMapper


class HandTracker:
    def __init__(self, mapper: CoordinateMapper | None = None) -> None:
        self._mapper = mapper or CoordinateMapper()
        self._hands: Any | None = None
        self._cv2: Any | None = None
        self._mp: Any | None = None
        self._mp_hands: Any | None = None
        self._backend: str | None = None
        self._last_timestamp_ms = 0

    @property
    def backend(self) -> str | None:
        return self._backend

    @staticmethod
    def model_path() -> Path:
        configured = (os.getenv("FRIDAY_MEDIAPIPE_HAND_MODEL") or "").strip()
        if configured:
            return Path(configured).expanduser().resolve()
        friday_root = Path(__file__).resolve().parents[3]
        return friday_root / "assets" / "models" / "vision" / "hand_landmarker.task"

    def _ensure_tracker(self) -> None:
        if self._hands is not None:
            return
        try:
            import cv2  # type: ignore
            import mediapipe as mp  # type: ignore
        except ImportError as exc:
            raise VisionDependencyError("mediapipe and opencv-python are required for hand tracking.") from exc
        self._cv2 = cv2
        self._mp = mp

        tasks = getattr(mp, "tasks", None)
        vision = getattr(tasks, "vision", None)
        if vision is not None and hasattr(vision, "HandLandmarker"):
            model_path = self.model_path()
            if not model_path.is_file():
                raise VisionDependencyError(
                    f"MediaPipe hand model was not found at {model_path}."
                )
            options = vision.HandLandmarkerOptions(
                base_options=tasks.BaseOptions(model_asset_path=str(model_path)),
                running_mode=vision.RunningMode.VIDEO,
                num_hands=2,
                min_hand_detection_confidence=0.55,
                min_hand_presence_confidence=0.55,
                min_tracking_confidence=0.55,
            )
            try:
                self._hands = vision.HandLandmarker.create_from_options(options)
            except (OSError, RuntimeError, ValueError) as exc:
                raise VisionDependencyError(
                    f"Unable to initialize MediaPipe Hand Landmarker from {model_path}."
                ) from exc
            self._backend = "tasks"
            return

        solutions = getattr(mp, "solutions", None)
        if solutions is None or not hasattr(solutions, "hands"):
            raise VisionDependencyError(
                "This MediaPipe build provides neither Hand Landmarker Tasks nor legacy Hands."
            )
        self._mp_hands = solutions.hands
        self._hands = self._mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=2,
            model_complexity=1,
            min_detection_confidence=0.55,
            min_tracking_confidence=0.55,
        )
        self._backend = "legacy"

    def detect(self, frame) -> list[dict[str, Any]]:
        self._ensure_tracker()
        rgb = self._cv2.cvtColor(frame, self._cv2.COLOR_BGR2RGB)
        if self._backend == "tasks":
            mp_image = self._mp.Image(
                image_format=self._mp.ImageFormat.SRGB,
                data=rgb,
            )
            timestamp_ms = max(
                self._last_timestamp_ms + 1,
                int(time.monotonic() * 1000),
            )
            self._last_timestamp_ms = timestamp_ms
            result = self._hands.detect_for_video(mp_image, timestamp_ms)
            return self._task_hands(result)

        result = self._hands.process(rgb)
        return self._legacy_hands(result)

    def _task_hands(self, result: Any) -> list[dict[str, Any]]:
        landmarks = getattr(result, "hand_landmarks", None) or []
        if not landmarks:
            return []

        hands: list[dict[str, Any]] = []
        handedness = getattr(result, "handedness", None) or []
        for index, hand_landmarks in enumerate(landmarks):
            label = "unknown"
            score = 0.0
            if index < len(handedness) and handedness[index]:
                category = handedness[index][0]
                raw_label = category.category_name or category.display_name or "unknown"
                label = str(raw_label).lower()
                score = float(category.score or 0.0)
            points = self._mapper.normalize_landmarks(hand_landmarks)
            hands.append({"hand": label, "hand_confidence": score, "points": points})
        return hands

    def _legacy_hands(self, result: Any) -> list[dict[str, Any]]:
        landmarks = getattr(result, "multi_hand_landmarks", None) or []
        if not landmarks:
            return []

        hands: list[dict[str, Any]] = []
        handedness = getattr(result, "multi_handedness", None) or []
        for index, hand_landmarks in enumerate(landmarks):
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
        self._backend = None
        self._last_timestamp_ms = 0
