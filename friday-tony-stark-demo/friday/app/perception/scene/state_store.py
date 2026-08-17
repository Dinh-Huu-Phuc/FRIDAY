from __future__ import annotations

from collections import Counter
from threading import RLock

from friday.app.perception.detection import SceneSnapshot, TargetLockState


class SceneStateStore:
    def __init__(self) -> None:
        self._lock = RLock()
        self._snapshot = SceneSnapshot.idle()

    def update(self, snapshot: SceneSnapshot) -> None:
        with self._lock:
            self._snapshot = snapshot

    def snapshot(self) -> SceneSnapshot:
        with self._lock:
            return self._snapshot

    def describe(self) -> str:
        snapshot = self.snapshot()
        if snapshot.status == "loading":
            return "Camera vision is warming up and loading the local detector, Boss."
        if snapshot.status == "disabled":
            return "Camera object detection is disabled in FRIDAY settings, Boss."
        if snapshot.status == "error":
            detail = snapshot.error or "the detector is unavailable"
            return f"I can access the camera, but {detail}"
        if snapshot.status != "ready":
            return "Open the FRIDAY Camera first so I can build a live scene state, Boss."
        if not snapshot.objects:
            return "The camera is active, but I do not currently detect a known object."

        counts = Counter(item.label for item in snapshot.objects)
        object_summary = ", ".join(
            f"{count} {label}{'' if count == 1 else 's'}"
            for label, count in sorted(counts.items())
        )
        target = snapshot.target_lock.target
        if target and snapshot.target_lock.state == TargetLockState.LOCKED:
            return (
                f"I can see {object_summary}. Target lock is on {target.label} "
                f"ID {target.track_id} at {target.confidence:.0%} confidence."
            )
        return f"I can see {object_summary}. I am still acquiring a stable target."
