from __future__ import annotations

from collections import Counter

from friday.app.perception.detection import SceneSnapshot, TargetLockState
from friday.app.perception.scene.schemas import (
    ObjectDepthTrend,
    ObjectMotionState,
    ObjectPresenceState,
    ObjectRelationType,
    TemporalObjectState,
    TemporalSceneSnapshot,
)


def summarize_scene(
    snapshot: SceneSnapshot,
    temporal: TemporalSceneSnapshot,
) -> str:
    if snapshot.status == "loading":
        return "Camera vision is warming up and loading the local detector, Boss."
    if snapshot.status == "disabled":
        return "Camera object detection is disabled in FRIDAY settings, Boss."
    if snapshot.status == "error":
        detail = snapshot.error or "the detector is unavailable"
        return f"I can access the camera, but {detail}"
    if snapshot.status != "ready":
        return "Open the FRIDAY Camera first so I can build a live scene state, Boss."

    visible = temporal.visible_objects
    occluded = tuple(
        item
        for item in temporal.objects
        if item.presence == ObjectPresenceState.OCCLUDED
    )
    if not visible:
        if occluded or snapshot.objects:
            return "The camera is active and temporarily recovering a lost track, Boss."
        return "The camera is active, but I do not currently detect a known object."

    counts = Counter(item.label for item in visible)
    object_summary = ", ".join(
        f"{count} {label}{'' if count == 1 else 's'}"
        for label, count in sorted(counts.items())
    )
    details = " ".join(_describe_object(item) for item in visible[:3])
    parts = [f"I can see {object_summary}.", details]

    target = snapshot.target_lock.target
    if target and snapshot.target_lock.state == TargetLockState.LOCKED:
        parts.append(
            f"Target lock is on {target.label} ID {target.track_id} "
            f"at {target.confidence:.0%} confidence."
        )
    elif snapshot.target_lock.state == TargetLockState.ACQUIRING:
        parts.append("I am still acquiring a stable target.")

    for relation in temporal.relations[:3]:
        if relation.relation_type == ObjectRelationType.HELD_BY_HAND:
            parts.append(
                f"The {relation.handedness} hand is holding "
                f"{relation.label} ID {relation.track_id}."
            )
        elif relation.relation_type == ObjectRelationType.POINTED_AT_BY_HAND:
            parts.append(
                f"The {relation.handedness} hand is pointing at "
                f"{relation.label} ID {relation.track_id}."
            )

    latest = temporal.recent_events[-1] if temporal.recent_events else None
    if latest and temporal.observed_at - latest.occurred_at <= 6.0:
        parts.append(f"Latest change: {latest.description}")
    elif temporal.stable_for_seconds >= 3.0:
        parts.append(
            f"No significant scene changes for {temporal.stable_for_seconds:.0f} seconds."
        )
    return " ".join(part for part in parts if part)


def _describe_object(item: TemporalObjectState) -> str:
    description = f"{item.label.capitalize()} ID {item.track_id} is in {item.position}"
    if item.motion == ObjectMotionState.MOVING:
        description += f", moving {item.movement_direction}"
    elif item.motion == ObjectMotionState.STATIONARY:
        description += ", stationary"
    if item.depth_trend == ObjectDepthTrend.APPROACHING:
        description += " and approaching the camera"
    elif item.depth_trend == ObjectDepthTrend.MOVING_AWAY:
        description += " and moving away from the camera"
    return description + "."
