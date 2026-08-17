from __future__ import annotations

from math import hypot

from friday.app.perception.detection.schemas import (
    TargetLock,
    TargetLockState,
    TrackedObject,
)


class TargetLocker:
    """Acquire and retain one salient tracked object for focused analysis."""

    def __init__(self, *, minimum_stable_frames: int = 2, lost_grace_frames: int = 3) -> None:
        self._minimum_stable_frames = max(1, minimum_stable_frames)
        self._lost_grace_frames = max(0, lost_grace_frames)
        self._candidate_id: int | None = None
        self._candidate_frames = 0
        self._locked_id: int | None = None
        self._locked_target: TrackedObject | None = None
        self._lost_frames = 0

    def update(
        self,
        objects: tuple[TrackedObject, ...],
        *,
        frame_width: int,
        frame_height: int,
    ) -> TargetLock:
        if self._locked_id is not None:
            current = next(
                (item for item in objects if item.track_id == self._locked_id),
                None,
            )
            if current is not None:
                self._locked_target = current
                self._lost_frames = 0
                return TargetLock(
                    state=TargetLockState.LOCKED,
                    target=current,
                    stable_frames=current.age_frames,
                )
            self._lost_frames += 1
            if self._lost_frames <= self._lost_grace_frames:
                return TargetLock(
                    state=TargetLockState.LOST,
                    target=self._locked_target,
                    stable_frames=0,
                )
            self._clear_lock()

        candidate = self._select_candidate(objects, frame_width, frame_height)
        if candidate is None:
            self._candidate_id = None
            self._candidate_frames = 0
            return TargetLock()
        if candidate.track_id == self._candidate_id:
            self._candidate_frames += 1
        else:
            self._candidate_id = candidate.track_id
            self._candidate_frames = 1

        if self._candidate_frames >= self._minimum_stable_frames:
            self._locked_id = candidate.track_id
            self._locked_target = candidate
            self._lost_frames = 0
            return TargetLock(
                state=TargetLockState.LOCKED,
                target=candidate,
                stable_frames=self._candidate_frames,
            )
        return TargetLock(
            state=TargetLockState.ACQUIRING,
            target=candidate,
            stable_frames=self._candidate_frames,
        )

    def reset(self) -> None:
        self._candidate_id = None
        self._candidate_frames = 0
        self._clear_lock()

    def _clear_lock(self) -> None:
        self._locked_id = None
        self._locked_target = None
        self._lost_frames = 0

    @staticmethod
    def _select_candidate(
        objects: tuple[TrackedObject, ...],
        frame_width: int,
        frame_height: int,
    ) -> TrackedObject | None:
        if not objects or frame_width <= 0 or frame_height <= 0:
            return None
        frame_area = frame_width * frame_height
        frame_center = (frame_width / 2, frame_height / 2)
        maximum_distance = hypot(frame_center[0], frame_center[1]) or 1.0

        def score(item: TrackedObject) -> float:
            center_x, center_y = item.box.center
            center_score = 1.0 - min(
                1.0,
                hypot(center_x - frame_center[0], center_y - frame_center[1])
                / maximum_distance,
            )
            area_score = min(1.0, item.box.area / max(1, frame_area) * 4)
            person_priority = 0.15 if item.label == "person" else 0.0
            return (
                item.confidence * 0.5
                + area_score * 0.25
                + center_score * 0.25
                + person_priority
            )

        return max(objects, key=score)
