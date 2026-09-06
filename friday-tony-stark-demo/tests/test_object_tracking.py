from friday.app.perception.detection import (
    BoundingBox,
    Detection,
    TargetLockState,
    TrackingState,
)
from friday.app.perception.tracking import ByteTracker, TargetLocker


def _person(x1: int, y1: int, x2: int, y2: int) -> Detection:
    return Detection(
        class_id=0,
        label="person",
        confidence=0.91,
        box=BoundingBox(x1, y1, x2, y2),
    )


def _chair(x1: int, y1: int, x2: int, y2: int) -> Detection:
    return Detection(
        class_id=56,
        label="chair",
        confidence=0.84,
        box=BoundingBox(x1, y1, x2, y2),
    )


def test_byte_tracker_keeps_id_and_reports_velocity_while_object_moves() -> None:
    tracker = ByteTracker(frame_rate=10)

    pending = tracker.update((_person(40, 30, 180, 220),), timestamp=1.0)
    first = tracker.update((_person(46, 34, 186, 224),), timestamp=1.1)
    second = tracker.update((_person(58, 40, 198, 230),), timestamp=1.2)

    assert pending == ()
    assert first[0].track_id == second[0].track_id
    assert second[0].age_frames == 2
    assert second[0].tracking_state == TrackingState.TRACKED
    assert second[0].velocity_x > 0
    assert second[0].velocity_y > 0


def test_byte_tracker_recovers_same_id_after_short_detection_gap() -> None:
    tracker = ByteTracker(frame_rate=10, lost_track_seconds=1.0)

    tracker.update((_person(40, 30, 180, 220),), timestamp=1.0)
    confirmed = tracker.update((_person(48, 30, 188, 220),), timestamp=1.1)
    lost = tracker.update((), timestamp=1.2)
    recovered = tracker.update((_person(64, 30, 204, 220),), timestamp=1.3)

    assert lost[0].track_id == confirmed[0].track_id
    assert lost[0].tracking_state == TrackingState.LOST
    assert lost[0].missed_frames == 1
    assert recovered[0].track_id == confirmed[0].track_id
    assert recovered[0].tracking_state == TrackingState.TRACKED
    assert recovered[0].missed_frames == 0


def test_prediction_tick_keeps_visible_track_active() -> None:
    tracker = ByteTracker(frame_rate=20)

    tracker.update((_person(40, 30, 180, 220),), timestamp=1.0)
    confirmed = tracker.update((_person(48, 30, 188, 220),), timestamp=1.1)
    predicted = tracker.predict(timestamp=1.15)

    assert predicted[0].track_id == confirmed[0].track_id
    assert predicted[0].tracking_state == TrackingState.TRACKED
    assert predicted[0].missed_frames == 0


def test_byte_tracker_preserves_ids_when_two_people_cross() -> None:
    tracker = ByteTracker(frame_rate=10)
    frames = (
        (_person(20, 20, 80, 180), _person(220, 20, 280, 180)),
        (_person(40, 20, 100, 180), _person(200, 20, 260, 180)),
        (_person(80, 20, 140, 180), _person(160, 20, 220, 180)),
        (_person(120, 20, 180, 180), _person(120, 20, 180, 180)),
        (_person(160, 20, 220, 180), _person(80, 20, 140, 180)),
        (_person(200, 20, 260, 180), _person(40, 20, 100, 180)),
    )

    tracked_frames = [
        tracker.update(frame, timestamp=1.0 + index * 0.1)
        for index, frame in enumerate(frames)
    ]

    first_confirmed = tracked_frames[1]
    final = tracked_frames[-1]
    right_moving_id = min(first_confirmed, key=lambda item: item.box.x1).track_id
    left_moving_id = max(first_confirmed, key=lambda item: item.box.x1).track_id
    assert max(final, key=lambda item: item.box.x1).track_id == right_moving_id
    assert min(final, key=lambda item: item.box.x1).track_id == left_moving_id


def test_byte_tracker_keeps_class_namespaces_isolated() -> None:
    tracker = ByteTracker(frame_rate=10)
    frame = (
        _person(40, 30, 180, 220),
        _chair(40, 30, 180, 220),
    )

    tracker.update(frame, timestamp=1.0)
    confirmed = tracker.update(frame, timestamp=1.1)

    assert {item.label for item in confirmed} == {"person", "chair"}
    assert len({item.track_id for item in confirmed}) == 2


def test_byte_tracker_expires_track_after_lost_buffer() -> None:
    tracker = ByteTracker(frame_rate=10, lost_track_seconds=0.3)

    tracker.update((_person(40, 30, 180, 220),), timestamp=1.0)
    original = tracker.update((_person(45, 30, 185, 220),), timestamp=1.1)
    tracker.update((), timestamp=1.2)
    expired = tracker.update((), timestamp=1.6)
    tracker.update((_person(55, 30, 195, 220),), timestamp=1.7)
    replacement = tracker.update((_person(60, 30, 200, 220),), timestamp=1.8)

    assert expired == ()
    assert replacement[0].track_id != original[0].track_id


def test_target_locker_acquires_locks_and_has_lost_grace() -> None:
    tracker = ByteTracker(frame_rate=10)
    locker = TargetLocker(minimum_stable_frames=2, lost_grace_frames=1)

    tracker.update((_person(40, 30, 180, 220),), timestamp=1.0)
    first_objects = tracker.update(
        (_person(45, 33, 185, 223),),
        timestamp=1.1,
    )
    acquiring = locker.update(first_objects, frame_width=320, frame_height=240)
    second_objects = tracker.update(
        (_person(50, 36, 190, 226),),
        timestamp=1.2,
    )
    locked = locker.update(second_objects, frame_width=320, frame_height=240)
    lost_objects = tracker.update((), timestamp=1.3)
    lost = locker.update(lost_objects, frame_width=320, frame_height=240)
    searching_objects = tracker.update((), timestamp=1.4)
    searching = locker.update(
        searching_objects,
        frame_width=320,
        frame_height=240,
    )

    assert acquiring.state == TargetLockState.ACQUIRING
    assert locked.state == TargetLockState.LOCKED
    assert locked.target is not None
    assert lost.state == TargetLockState.LOST
    assert lost.target is not None
    assert lost.target.tracking_state == TrackingState.LOST
    assert searching.state == TargetLockState.SEARCHING


def test_target_locker_prediction_does_not_advance_acquisition() -> None:
    tracker = ByteTracker(frame_rate=20)
    locker = TargetLocker(minimum_stable_frames=2)

    tracker.update((_person(40, 30, 180, 220),), timestamp=1.0)
    detected = tracker.update((_person(45, 30, 185, 220),), timestamp=1.1)
    acquiring = locker.update(detected, frame_width=320, frame_height=240)
    predicted = locker.predict(tracker.predict(timestamp=1.15))

    assert acquiring.state == TargetLockState.ACQUIRING
    assert predicted.state == TargetLockState.ACQUIRING
    assert predicted.stable_frames == acquiring.stable_frames == 1
