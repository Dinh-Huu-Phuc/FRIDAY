from friday.app.perception.detection import (
    BoundingBox,
    SceneSnapshot,
    TrackedObject,
    TrackingState,
)
from friday.app.perception.scene import (
    ObjectDepthTrend,
    ObjectMotionState,
    ObjectPresenceState,
    SceneEventConfig,
    SceneEventDetector,
    SceneEventType,
    SceneStateStore,
)


def _tracked(
    *,
    track_id: int = 4,
    box: BoundingBox | None = None,
    velocity_x: float = 0.0,
    velocity_y: float = 0.0,
    state: TrackingState = TrackingState.TRACKED,
) -> TrackedObject:
    return TrackedObject(
        track_id=track_id,
        class_id=0,
        label="person",
        confidence=0.93,
        box=box or BoundingBox(150, 80, 250, 220),
        age_frames=3,
        velocity_x=velocity_x,
        velocity_y=velocity_y,
        tracking_state=state,
    )


def _snapshot(
    timestamp: float,
    sequence: int,
    objects: tuple[TrackedObject, ...],
    *,
    detector_sampled: bool = True,
) -> SceneSnapshot:
    return SceneSnapshot(
        sequence=sequence,
        captured_at=timestamp,
        frame_width=400,
        frame_height=300,
        objects=objects,
        detector_sampled=detector_sampled,
        status="ready",
    )


def _config(**overrides: object) -> SceneEventConfig:
    values = {
        "disappear_after_seconds": 0.5,
        "event_retention_seconds": 30.0,
        "object_retention_seconds": 60.0,
        "moving_enter_speed": 0.03,
        "moving_exit_speed": 0.01,
        "motion_confirmation_frames": 2,
        "depth_change_rate": 0.2,
        "depth_confirmation_frames": 2,
        "maximum_events": 32,
    }
    values.update(overrides)
    return SceneEventConfig(**values)


def test_object_appearance_is_emitted_once_and_prediction_is_not_evidence() -> None:
    detector = SceneEventDetector(_config())

    first = detector.update(_snapshot(10.0, 1, (_tracked(),)))
    predicted = detector.update(
        _snapshot(10.1, 1, (_tracked(),), detector_sampled=False)
    )

    assert [event.event_type for event in first.recent_events] == [
        SceneEventType.OBJECT_APPEARED
    ]
    assert len(predicted.recent_events) == 1
    assert predicted.objects[0].last_seen_at == 10.0
    assert predicted.objects[0].presence == ObjectPresenceState.VISIBLE


def test_disappearance_requires_real_detector_samples_after_grace_period() -> None:
    detector = SceneEventDetector(_config(disappear_after_seconds=0.5))

    detector.update(_snapshot(10.0, 1, (_tracked(),)))
    occluded = detector.update(_snapshot(10.1, 2, ()))
    prediction = detector.update(
        _snapshot(11.0, 2, (), detector_sampled=False)
    )
    absent = detector.update(_snapshot(11.0, 3, ()))

    assert occluded.objects[0].presence == ObjectPresenceState.OCCLUDED
    assert prediction.objects[0].presence == ObjectPresenceState.OCCLUDED
    assert absent.objects[0].presence == ObjectPresenceState.ABSENT
    assert absent.recent_events[-1].event_type == SceneEventType.OBJECT_DISAPPEARED


def test_absent_track_can_reappear_with_the_same_identity() -> None:
    detector = SceneEventDetector(_config(disappear_after_seconds=0.2))

    detector.update(_snapshot(10.0, 1, (_tracked(),)))
    detector.update(_snapshot(10.1, 2, ()))
    detector.update(_snapshot(10.4, 3, ()))
    reappeared = detector.update(_snapshot(10.5, 4, (_tracked(),)))

    assert reappeared.objects[0].presence == ObjectPresenceState.VISIBLE
    assert reappeared.objects[0].track_id == 4
    assert reappeared.recent_events[-1].event_type == SceneEventType.OBJECT_REAPPEARED


def test_motion_state_uses_hysteresis_and_confirmation_frames() -> None:
    detector = SceneEventDetector(_config(depth_change_rate=99.0))

    detector.update(_snapshot(10.0, 1, (_tracked(),)))
    detector.update(
        _snapshot(10.1, 2, (_tracked(velocity_x=30.0),))
    )
    moving = detector.update(
        _snapshot(10.2, 3, (_tracked(velocity_x=30.0),))
    )
    detector.update(_snapshot(10.3, 4, (_tracked(),)))
    stopped = detector.update(_snapshot(10.4, 5, (_tracked(),)))

    assert moving.objects[0].motion == ObjectMotionState.MOVING
    assert moving.objects[0].movement_direction == "right"
    assert SceneEventType.OBJECT_STARTED_MOVING in {
        event.event_type for event in moving.recent_events
    }
    assert stopped.objects[0].motion == ObjectMotionState.STATIONARY
    assert stopped.recent_events[-1].event_type == SceneEventType.OBJECT_STOPPED_MOVING


def test_box_area_history_detects_approaching_and_moving_away() -> None:
    detector = SceneEventDetector(_config(depth_change_rate=0.2))

    detector.update(
        _snapshot(10.0, 1, (_tracked(box=BoundingBox(175, 100, 225, 200)),))
    )
    detector.update(
        _snapshot(10.1, 2, (_tracked(box=BoundingBox(170, 90, 230, 210)),))
    )
    approaching = detector.update(
        _snapshot(10.2, 3, (_tracked(box=BoundingBox(165, 80, 235, 220)),))
    )
    detector.update(
        _snapshot(10.3, 4, (_tracked(box=BoundingBox(170, 90, 230, 210)),))
    )
    moving_away = detector.update(
        _snapshot(10.4, 5, (_tracked(box=BoundingBox(175, 100, 225, 200)),))
    )

    assert approaching.objects[0].depth_trend == ObjectDepthTrend.APPROACHING
    assert moving_away.objects[0].depth_trend == ObjectDepthTrend.MOVING_AWAY
    assert moving_away.recent_events[-1].event_type == SceneEventType.OBJECT_MOVING_AWAY


def test_scene_store_exposes_temporal_context_to_agent_description() -> None:
    store = SceneStateStore(SceneEventDetector(_config()))

    store.update(_snapshot(10.0, 1, (_tracked(),)))
    store.update(
        _snapshot(10.1, 2, (_tracked(velocity_x=30.0),))
    )
    store.update(
        _snapshot(10.2, 3, (_tracked(velocity_x=30.0),))
    )

    temporal = store.temporal_snapshot()
    description = store.describe()

    assert temporal.visible_objects[0].position == "the center"
    assert temporal.visible_objects[0].motion == ObjectMotionState.MOVING
    assert "moving right" in description
    assert "Latest change" in description
