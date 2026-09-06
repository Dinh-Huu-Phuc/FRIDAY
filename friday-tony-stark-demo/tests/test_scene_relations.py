from friday.app.perception.detection import BoundingBox, SceneSnapshot, TrackedObject
from friday.app.perception.relation import (
    HandObservationProvider,
    RelationEngineConfig,
    SceneRelationEngine,
)
from friday.app.perception.scene import (
    HandObservation,
    ObjectDepthTrend,
    ObjectMotionState,
    ObjectPresenceState,
    ObjectRelationType,
    SceneEventDetector,
    SceneEventType,
    SceneStateStore,
    TemporalObjectState,
    TemporalSceneSnapshot,
)
from friday.core.schemas.spatial_entities import FingerState


def _object(
    *,
    track_id: int = 7,
    label: str = "bottle",
    box: BoundingBox | None = None,
) -> TemporalObjectState:
    return TemporalObjectState(
        track_id=track_id,
        class_id=39 if label == "bottle" else 0,
        label=label,
        confidence=0.92,
        box=box or BoundingBox(200, 100, 300, 200),
        presence=ObjectPresenceState.VISIBLE,
        motion=ObjectMotionState.STATIONARY,
        depth_trend=ObjectDepthTrend.STABLE,
        position="the center",
        movement_direction="none",
        normalized_speed=0.0,
        first_seen_at=10.0,
        last_seen_at=10.0,
        visible_since=10.0,
        unseen_since=None,
        age_seconds=1.0,
    )


def _scene(
    timestamp: float,
    objects: tuple[TemporalObjectState, ...],
) -> TemporalSceneSnapshot:
    return TemporalSceneSnapshot(
        observed_at=timestamp,
        status="ready",
        objects=objects,
        last_significant_change_at=timestamp,
    )


def _hand(
    *,
    gripping: bool = False,
    pointing: bool = False,
) -> HandObservation:
    return HandObservation(
        hand_id="right-1",
        handedness="right",
        confidence=0.94,
        gesture="grab" if gripping else "idle",
        is_pointing=pointing,
        is_gripping=gripping,
        palm_x=0.55,
        palm_y=0.50,
        interaction_x=0.55,
        interaction_y=0.50,
        index_base_x=0.10,
        index_base_y=0.50,
        index_tip_x=0.30,
        index_tip_y=0.50,
    )


def _config(**overrides: object) -> RelationEngineConfig:
    values = {
        "hold_confirmation_frames": 2,
        "release_confirmation_frames": 2,
        "point_confirmation_frames": 2,
        "grip_target_radius": 0.12,
        "point_tolerance": 0.07,
        "event_retention_seconds": 30.0,
        "maximum_events": 32,
    }
    values.update(overrides)
    return RelationEngineConfig(**values)


def test_hold_and_place_events_require_confirmation_frames() -> None:
    engine = SceneRelationEngine(_config())
    target = _object()

    first_relations, _ = engine.update(
        _scene(10.0, (target,)),
        hand_observations=(_hand(gripping=True),),
        frame_width=400,
        frame_height=300,
    )
    held_relations, held_events = engine.update(
        _scene(10.1, (target,)),
        hand_observations=(_hand(gripping=True),),
        frame_width=400,
        frame_height=300,
    )
    releasing_relations, _ = engine.update(
        _scene(10.2, (target,)),
        hand_observations=(_hand(),),
        frame_width=400,
        frame_height=300,
    )
    placed_relations, placed_events = engine.update(
        _scene(10.3, (target,)),
        hand_observations=(_hand(),),
        frame_width=400,
        frame_height=300,
    )

    assert first_relations == ()
    assert held_relations[0].relation_type == ObjectRelationType.HELD_BY_HAND
    assert held_events[-1].event_type == SceneEventType.OBJECT_HELD
    assert releasing_relations[0].relation_type == ObjectRelationType.HELD_BY_HAND
    assert placed_relations == ()
    assert placed_events[-1].event_type == SceneEventType.OBJECT_PLACED_DOWN


def test_pointing_ray_selects_object_and_does_not_repeat_event() -> None:
    engine = SceneRelationEngine(_config(point_confirmation_frames=2))
    target = _object()

    engine.update(
        _scene(10.0, (target,)),
        hand_observations=(_hand(pointing=True),),
        frame_width=400,
        frame_height=300,
    )
    relations, events = engine.update(
        _scene(10.1, (target,)),
        hand_observations=(_hand(pointing=True),),
        frame_width=400,
        frame_height=300,
    )
    _, continued_events = engine.update(
        _scene(10.2, (target,)),
        hand_observations=(_hand(pointing=True),),
        frame_width=400,
        frame_height=300,
    )

    assert relations[0].relation_type == ObjectRelationType.POINTED_AT_BY_HAND
    assert relations[0].track_id == target.track_id
    assert events[-1].event_type == SceneEventType.OBJECT_POINTED_AT
    assert len(continued_events) == len(events)


def test_people_count_change_is_reported_after_initial_baseline() -> None:
    engine = SceneRelationEngine(_config())
    first_person = _object(track_id=1, label="person")
    second_person = _object(
        track_id=2,
        label="person",
        box=BoundingBox(40, 80, 140, 220),
    )

    _, initial_events = engine.update(
        _scene(10.0, (first_person,)),
        hand_observations=None,
        frame_width=400,
        frame_height=300,
    )
    _, changed_events = engine.update(
        _scene(10.1, (first_person, second_person)),
        hand_observations=None,
        frame_width=400,
        frame_height=300,
    )

    assert initial_events == ()
    assert changed_events[-1].event_type == SceneEventType.PEOPLE_COUNT_CHANGED
    assert "from 1 to 2" in changed_events[-1].description


def test_prediction_snapshot_does_not_advance_hand_release() -> None:
    relation_engine = SceneRelationEngine(
        _config(hold_confirmation_frames=1, release_confirmation_frames=1)
    )
    store = SceneStateStore(
        SceneEventDetector(),
        relation_engine=relation_engine,
    )
    bottle = TrackedObject(
        track_id=7,
        class_id=39,
        label="bottle",
        confidence=0.92,
        box=BoundingBox(200, 100, 300, 200),
    )
    observed = SceneSnapshot(
        sequence=1,
        captured_at=10.0,
        frame_width=400,
        frame_height=300,
        objects=(bottle,),
        status="ready",
    )
    predicted = SceneSnapshot(
        sequence=1,
        captured_at=10.1,
        frame_width=400,
        frame_height=300,
        objects=(bottle,),
        detector_sampled=False,
        status="ready",
    )

    store.update(observed, hand_observations=(_hand(gripping=True),))
    store.update(predicted)

    assert store.temporal_snapshot().relations[0].relation_type == (
        ObjectRelationType.HELD_BY_HAND
    )
    assert "holding bottle ID 7" in store.describe()


class _FakeHandTracker:
    def detect(self, frame: object) -> list[dict[str, object]]:
        del frame
        points = {
            0: (0.4, 0.6, 0.0),
            4: (0.5, 0.5, 0.0),
            5: (0.3, 0.5, 0.0),
            8: (0.6, 0.5, 0.0),
            9: (0.4, 0.5, 0.0),
        }
        return [{"hand": "right", "hand_confidence": 0.9, "points": points}]

    def close(self) -> None:
        return


class _FakeGestureEngine:
    def classify(
        self,
        points: object,
    ) -> tuple[str, float, FingerState]:
        del points
        return "idle", 0.0, FingerState(index=True)


def test_hand_observer_converts_landmarks_to_pointing_observation() -> None:
    provider = HandObservationProvider(
        tracker=_FakeHandTracker(),
        gesture_engine=_FakeGestureEngine(),
    )

    observations = provider.detect(object())

    assert observations[0].hand_id == "right-1"
    assert observations[0].is_pointing is True
    assert observations[0].is_gripping is False
    assert observations[0].index_tip_x == 0.6
