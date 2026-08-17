from friday.app.perception.detection import BoundingBox, Detection, TargetLockState
from friday.app.perception.tracking import IoUTracker, TargetLocker


def _person(x1: int, y1: int, x2: int, y2: int) -> Detection:
    return Detection(
        class_id=0,
        label="person",
        confidence=0.91,
        box=BoundingBox(x1, y1, x2, y2),
    )


def test_iou_tracker_keeps_id_while_object_moves() -> None:
    tracker = IoUTracker()

    first = tracker.update((_person(40, 30, 180, 220),))
    second = tracker.update((_person(46, 34, 186, 224),))

    assert first[0].track_id == second[0].track_id
    assert second[0].age_frames == 2


def test_target_locker_acquires_locks_and_has_lost_grace() -> None:
    tracker = IoUTracker()
    locker = TargetLocker(minimum_stable_frames=2, lost_grace_frames=1)

    first_objects = tracker.update((_person(40, 30, 180, 220),))
    acquiring = locker.update(first_objects, frame_width=320, frame_height=240)
    second_objects = tracker.update((_person(45, 33, 185, 223),))
    locked = locker.update(second_objects, frame_width=320, frame_height=240)
    lost = locker.update((), frame_width=320, frame_height=240)
    searching = locker.update((), frame_width=320, frame_height=240)

    assert acquiring.state == TargetLockState.ACQUIRING
    assert locked.state == TargetLockState.LOCKED
    assert locked.target is not None
    assert lost.state == TargetLockState.LOST
    assert searching.state == TargetLockState.SEARCHING
