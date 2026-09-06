from __future__ import annotations

import os
import time
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from friday.app.perception.detection.schemas import (
    BoundingBox,
    Detection,
    TrackedObject,
    TrackingState,
)

TrackerFactory = Callable[..., Any]


class TrackingDependencyError(RuntimeError):
    """Raised when the maintained ByteTrack runtime cannot be loaded."""


@dataclass(slots=True)
class _TrackMetadata:
    class_id: int
    label: str
    confidence: float
    box: BoundingBox
    last_observed_box: BoundingBox
    age_frames: int = 1
    missed_frames: int = 0
    last_seen_at: float = 0.0
    velocity_x: float = 0.0
    velocity_y: float = 0.0


class ByteTracker:
    """Adapt Roboflow ByteTrack to FRIDAY's detector-domain objects."""

    def __init__(
        self,
        *,
        frame_rate: float,
        lost_track_seconds: float = 1.0,
        track_activation_threshold: float = 0.5,
        high_confidence_threshold: float = 0.55,
        minimum_iou_threshold: float = 0.1,
        minimum_consecutive_frames: int = 2,
        tracker_factory: TrackerFactory | None = None,
    ) -> None:
        try:
            import numpy as np
            import supervision as sv
            from trackers import ByteTrackTracker
        except ImportError as exc:
            raise TrackingDependencyError(
                "The 'trackers' and 'supervision' packages are required for ByteTrack."
            ) from exc

        self._np = np
        self._sv = sv
        self._tracker_factory = tracker_factory or ByteTrackTracker
        self._frame_rate = max(1.0, float(frame_rate))
        self._lost_track_seconds = max(0.0, float(lost_track_seconds))
        self._lost_track_buffer = round(self._lost_track_seconds * 30)
        self._activation_threshold = _clamp(track_activation_threshold, 0.01, 0.99)
        self._high_confidence_threshold = _clamp(
            high_confidence_threshold,
            0.01,
            0.99,
        )
        self._minimum_iou_threshold = _clamp(minimum_iou_threshold, 0.01, 0.99)
        self._minimum_consecutive_frames = max(1, minimum_consecutive_frames)
        self._trackers: dict[int, Any] = {}
        self._external_ids: dict[tuple[int, int], int] = {}
        self._metadata: dict[int, _TrackMetadata] = {}
        self._next_track_id = 1

    @classmethod
    def from_environment(cls, *, frame_rate: float) -> ByteTracker:
        return cls(
            frame_rate=frame_rate,
            lost_track_seconds=_environment_float(
                "FRIDAY_VISION_TRACK_LOST_SECONDS",
                1.0,
                minimum=0.0,
                maximum=10.0,
            ),
            track_activation_threshold=_environment_float(
                "FRIDAY_VISION_TRACK_ACTIVATION_THRESHOLD",
                0.5,
                minimum=0.01,
                maximum=0.99,
            ),
            high_confidence_threshold=_environment_float(
                "FRIDAY_VISION_TRACK_HIGH_CONFIDENCE_THRESHOLD",
                0.55,
                minimum=0.01,
                maximum=0.99,
            ),
            minimum_iou_threshold=_environment_float(
                "FRIDAY_VISION_TRACK_IOU_THRESHOLD",
                0.1,
                minimum=0.01,
                maximum=0.99,
            ),
            minimum_consecutive_frames=_environment_int(
                "FRIDAY_VISION_TRACK_MIN_FRAMES",
                2,
                minimum=1,
                maximum=10,
            ),
        )

    def update(
        self,
        detections: tuple[Detection, ...],
        *,
        timestamp: float | None = None,
    ) -> tuple[TrackedObject, ...]:
        observed_at = time.monotonic() if timestamp is None else float(timestamp)
        return self._advance(
            detections,
            timestamp=observed_at,
            prediction_only=False,
        )

    def predict(self, *, timestamp: float | None = None) -> tuple[TrackedObject, ...]:
        """Advance Kalman state between detector samples without declaring a miss."""

        observed_at = time.monotonic() if timestamp is None else float(timestamp)
        return self._advance((), timestamp=observed_at, prediction_only=True)

    def _advance(
        self,
        detections: tuple[Detection, ...],
        *,
        timestamp: float,
        prediction_only: bool,
    ) -> tuple[TrackedObject, ...]:
        detections_by_class: dict[int, list[Detection]] = defaultdict(list)
        for detection in detections:
            detections_by_class[detection.class_id].append(detection)

        class_ids = set(self._trackers) | set(detections_by_class)
        output: list[TrackedObject] = []
        alive_ids: set[int] = set()
        for class_id in sorted(class_ids):
            tracker = self._trackers.get(class_id)
            if tracker is None:
                tracker = self._create_tracker()
                self._trackers[class_id] = tracker
            current = self._as_supervision_detections(
                detections_by_class.get(class_id, [])
            )
            matched = tracker.update(current, timestamp=timestamp)
            current_by_id = self._current_detections_by_id(matched)
            predicted = tracker.tracked_objects
            tracker_ids = predicted.tracker_id
            if tracker_ids is None:
                continue
            for index, local_track_id in enumerate(tracker_ids):
                local_id = int(local_track_id)
                global_id = self._global_track_id(class_id, local_id)
                alive_ids.add(global_id)
                if local_id in current_by_id:
                    output.append(
                        self._update_observed_track(
                            global_id,
                            class_id,
                            current_by_id[local_id],
                            timestamp,
                        )
                    )
                else:
                    predicted_box = self._box_from_xyxy(predicted.xyxy[index])
                    lost = self._update_unobserved_track(
                        global_id,
                        predicted_box,
                        prediction_only=prediction_only,
                    )
                    if lost is not None:
                        output.append(lost)

        for global_id in set(self._metadata) - alive_ids:
            del self._metadata[global_id]
        return tuple(
            sorted(
                output,
                key=lambda item: (
                    item.tracking_state == TrackingState.LOST,
                    item.track_id,
                ),
            )
        )

    def reset(self) -> None:
        for tracker in self._trackers.values():
            tracker.reset()
        self._trackers.clear()
        self._external_ids.clear()
        self._metadata.clear()
        self._next_track_id = 1

    def _create_tracker(self) -> Any:
        return self._tracker_factory(
            lost_track_buffer=self._lost_track_buffer,
            frame_rate=self._frame_rate,
            track_activation_threshold=self._activation_threshold,
            minimum_consecutive_frames=self._minimum_consecutive_frames,
            minimum_iou_threshold=self._minimum_iou_threshold,
            high_conf_det_threshold=self._high_confidence_threshold,
        )

    def _as_supervision_detections(self, detections: list[Detection]) -> Any:
        if not detections:
            return self._sv.Detections.empty()
        return self._sv.Detections(
            xyxy=self._np.asarray(
                [
                    (item.box.x1, item.box.y1, item.box.x2, item.box.y2)
                    for item in detections
                ],
                dtype=self._np.float32,
            ),
            confidence=self._np.asarray(
                [item.confidence for item in detections],
                dtype=self._np.float32,
            ),
            class_id=self._np.asarray(
                [item.class_id for item in detections],
                dtype=int,
            ),
            data={
                "label": self._np.asarray(
                    [item.label for item in detections],
                    dtype=object,
                )
            },
        )

    def _current_detections_by_id(
        self,
        detections: Any,
    ) -> dict[int, tuple[BoundingBox, float, str]]:
        tracker_ids = detections.tracker_id
        if tracker_ids is None:
            return {}
        labels = detections.data.get("label")
        confidence = detections.confidence
        current: dict[int, tuple[BoundingBox, float, str]] = {}
        for index, tracker_id in enumerate(tracker_ids):
            local_id = int(tracker_id)
            if local_id < 0:
                continue
            label = str(labels[index]) if labels is not None else "object"
            score = float(confidence[index]) if confidence is not None else 0.0
            current[local_id] = (
                self._box_from_xyxy(detections.xyxy[index]),
                score,
                label,
            )
        return current

    def _global_track_id(self, class_id: int, local_track_id: int) -> int:
        key = (class_id, local_track_id)
        global_id = self._external_ids.get(key)
        if global_id is None:
            global_id = self._next_track_id
            self._next_track_id += 1
            self._external_ids[key] = global_id
        return global_id

    def _update_observed_track(
        self,
        track_id: int,
        class_id: int,
        current: tuple[BoundingBox, float, str],
        observed_at: float,
    ) -> TrackedObject:
        box, confidence, label = current
        metadata = self._metadata.get(track_id)
        if metadata is None:
            metadata = _TrackMetadata(
                class_id=class_id,
                label=label,
                confidence=confidence,
                box=box,
                last_observed_box=box,
                last_seen_at=observed_at,
            )
            self._metadata[track_id] = metadata
        else:
            elapsed = max(1e-6, observed_at - metadata.last_seen_at)
            previous_x, previous_y = metadata.last_observed_box.center
            current_x, current_y = box.center
            measured_x = (current_x - previous_x) / elapsed
            measured_y = (current_y - previous_y) / elapsed
            metadata.velocity_x = metadata.velocity_x * 0.35 + measured_x * 0.65
            metadata.velocity_y = metadata.velocity_y * 0.35 + measured_y * 0.65
            metadata.label = label
            metadata.confidence = confidence
            metadata.box = box
            metadata.last_observed_box = box
            metadata.age_frames += 1
            metadata.missed_frames = 0
            metadata.last_seen_at = observed_at
        state = (
            TrackingState.DETECTED
            if metadata.age_frames == 1
            else TrackingState.TRACKED
        )
        return self._to_object(track_id, metadata, state)

    def _update_unobserved_track(
        self,
        track_id: int,
        predicted_box: BoundingBox,
        *,
        prediction_only: bool,
    ) -> TrackedObject | None:
        metadata = self._metadata.get(track_id)
        if metadata is None:
            return None
        metadata.box = predicted_box
        metadata.age_frames += 1
        if not prediction_only:
            metadata.missed_frames += 1
        state = (
            TrackingState.TRACKED
            if prediction_only and metadata.missed_frames == 0
            else TrackingState.LOST
        )
        return self._to_object(track_id, metadata, state)

    @staticmethod
    def _to_object(
        track_id: int,
        metadata: _TrackMetadata,
        state: TrackingState,
    ) -> TrackedObject:
        return TrackedObject(
            track_id=track_id,
            class_id=metadata.class_id,
            label=metadata.label,
            confidence=metadata.confidence,
            box=metadata.box,
            age_frames=metadata.age_frames,
            missed_frames=metadata.missed_frames,
            velocity_x=metadata.velocity_x,
            velocity_y=metadata.velocity_y,
            tracking_state=state,
        )

    @staticmethod
    def _box_from_xyxy(values: Any) -> BoundingBox:
        return BoundingBox(*(round(float(value)) for value in values[:4]))


def _environment_float(
    name: str,
    default: float,
    *,
    minimum: float,
    maximum: float,
) -> float:
    try:
        value = float(os.getenv(name, str(default)).strip())
    except ValueError:
        return default
    return _clamp(value, minimum, maximum)


def _environment_int(
    name: str,
    default: int,
    *,
    minimum: int,
    maximum: int,
) -> int:
    try:
        value = int(os.getenv(name, str(default)).strip())
    except ValueError:
        return default
    return min(maximum, max(minimum, value))


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return min(maximum, max(minimum, float(value)))
