from __future__ import annotations

from dataclasses import dataclass

from friday.app.perception.detection.schemas import (
    BoundingBox,
    Detection,
    TrackedObject,
)


@dataclass(slots=True)
class _Track:
    track_id: int
    class_id: int
    label: str
    confidence: float
    box: BoundingBox
    age_frames: int = 1
    missed_frames: int = 0


class IoUTracker:
    """A small CPU tracker that stabilizes detector IDs without extra models."""

    def __init__(
        self,
        *,
        iou_threshold: float = 0.25,
        max_missed_frames: int = 5,
        smoothing: float = 0.72,
    ) -> None:
        self._iou_threshold = iou_threshold
        self._max_missed_frames = max_missed_frames
        self._smoothing = smoothing
        self._next_track_id = 1
        self._tracks: dict[int, _Track] = {}

    def update(self, detections: tuple[Detection, ...]) -> tuple[TrackedObject, ...]:
        unmatched_track_ids = set(self._tracks)
        output: list[TrackedObject] = []

        for detection in detections:
            candidates = [
                track
                for track in self._tracks.values()
                if track.track_id in unmatched_track_ids
                and track.class_id == detection.class_id
            ]
            best_track = max(
                candidates,
                key=lambda track: track.box.iou(detection.box),
                default=None,
            )
            best_iou = best_track.box.iou(detection.box) if best_track else 0.0
            if best_track is None or best_iou < self._iou_threshold:
                best_track = _Track(
                    track_id=self._next_track_id,
                    class_id=detection.class_id,
                    label=detection.label,
                    confidence=detection.confidence,
                    box=detection.box,
                )
                self._tracks[best_track.track_id] = best_track
                self._next_track_id += 1
            else:
                unmatched_track_ids.discard(best_track.track_id)
                best_track.box = self._smooth_box(best_track.box, detection.box)
                best_track.confidence = detection.confidence
                best_track.age_frames += 1
                best_track.missed_frames = 0

            output.append(self._to_object(best_track))

        active_ids = {item.track_id for item in output}
        for track_id, track in tuple(self._tracks.items()):
            if track_id in active_ids:
                continue
            track.missed_frames += 1
            if track.missed_frames > self._max_missed_frames:
                del self._tracks[track_id]

        return tuple(output)

    def reset(self) -> None:
        self._tracks.clear()
        self._next_track_id = 1

    def _smooth_box(self, previous: BoundingBox, current: BoundingBox) -> BoundingBox:
        old_weight = 1.0 - self._smoothing
        return BoundingBox(
            x1=round(previous.x1 * old_weight + current.x1 * self._smoothing),
            y1=round(previous.y1 * old_weight + current.y1 * self._smoothing),
            x2=round(previous.x2 * old_weight + current.x2 * self._smoothing),
            y2=round(previous.y2 * old_weight + current.y2 * self._smoothing),
        )

    @staticmethod
    def _to_object(track: _Track) -> TrackedObject:
        return TrackedObject(
            track_id=track.track_id,
            class_id=track.class_id,
            label=track.label,
            confidence=track.confidence,
            box=track.box,
            age_frames=track.age_frames,
        )
