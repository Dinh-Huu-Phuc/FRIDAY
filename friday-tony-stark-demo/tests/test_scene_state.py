from friday.app.perception.detection import (
    BoundingBox,
    SceneSnapshot,
    TargetLock,
    TargetLockState,
    TrackedObject,
    TrackingState,
)
from friday.app.perception.scene import SceneStateStore


def test_scene_description_reports_objects_and_locked_target() -> None:
    person = TrackedObject(
        track_id=4,
        class_id=0,
        label="person",
        confidence=0.93,
        box=BoundingBox(10, 10, 100, 180),
        age_frames=3,
    )
    store = SceneStateStore()
    store.update(
        SceneSnapshot(
            status="ready",
            objects=(person,),
            target_lock=TargetLock(
                state=TargetLockState.LOCKED,
                target=person,
                stable_frames=3,
            ),
        )
    )

    description = store.describe()

    assert "1 person" in description
    assert "Target lock is on person ID 4" in description


def test_scene_description_does_not_report_predicted_lost_track_as_visible() -> None:
    store = SceneStateStore()
    store.update(
        SceneSnapshot(
            status="ready",
            objects=(
                TrackedObject(
                    track_id=4,
                    class_id=0,
                    label="person",
                    confidence=0.93,
                    box=BoundingBox(10, 10, 100, 180),
                    age_frames=4,
                    missed_frames=1,
                    tracking_state=TrackingState.LOST,
                ),
            ),
        )
    )

    assert "temporarily recovering a lost track" in store.describe()
