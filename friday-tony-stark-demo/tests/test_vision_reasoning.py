from __future__ import annotations

import asyncio
import base64
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from friday.app.agent_console.schemas import ConsoleChatRequest
from friday.app.perception.detection import BoundingBox, SceneSnapshot
from friday.app.perception.reasoning import (
    GemmaVisionClient,
    GemmaVisionOutput,
    KeyframePolicy,
    KeyframePolicyConfig,
    KeyframeReason,
    KeyframeStore,
    VisionKeyframe,
    VisionModelError,
    VisionReasoningResult,
    VisionReasoningStatus,
    VisionRouter,
)
from friday.app.perception.scene import (
    ObjectDepthTrend,
    ObjectMotionState,
    ObjectPresenceState,
    SceneEvent,
    SceneEventType,
    SceneStateStore,
    TemporalObjectState,
    TemporalSceneSnapshot,
)
from friday.app.perception.service import PerceptionService
from friday.src.services.agent.service import chat


def _object(*, confidence: float = 0.9) -> TemporalObjectState:
    return TemporalObjectState(
        track_id=7,
        class_id=39,
        label="bottle",
        confidence=confidence,
        box=BoundingBox(20, 20, 80, 140),
        presence=ObjectPresenceState.VISIBLE,
        motion=ObjectMotionState.STATIONARY,
        depth_trend=ObjectDepthTrend.STABLE,
        position="the left side",
        movement_direction="none",
        normalized_speed=0.0,
        first_seen_at=1.0,
        last_seen_at=10.0,
        visible_since=1.0,
        unseen_since=None,
        age_seconds=9.0,
    )


def _snapshot(*, captured_at: float = 10.0, sequence: int = 4) -> SceneSnapshot:
    return SceneSnapshot(
        sequence=sequence,
        captured_at=captured_at,
        frame_width=640,
        frame_height=360,
        status="ready",
    )


def _temporal(
    *,
    confidence: float = 0.9,
    event: SceneEvent | None = None,
) -> TemporalSceneSnapshot:
    return TemporalSceneSnapshot(
        observed_at=10.0,
        status="ready",
        objects=(_object(confidence=confidence),),
        recent_events=(event,) if event else (),
        last_significant_change_at=1.0,
        stable_for_seconds=9.0,
    )


def _keyframe(*, sequence: int = 4) -> VisionKeyframe:
    return VisionKeyframe(
        sequence=sequence,
        captured_at=10.0,
        frame_width=640,
        frame_height=360,
        reason=KeyframeReason.USER_REQUEST,
        scene_summary="I can see one bottle.",
        scene_signature=(("bottle", 1),),
        jpeg_bytes=b"jpeg-data",
    )


def test_keyframe_policy_selects_initial_event_and_user_frames() -> None:
    policy = KeyframePolicy(
        KeyframePolicyConfig(
            minimum_interval_seconds=1.0,
            maximum_interval_seconds=8.0,
            low_confidence_threshold=0.5,
        )
    )
    initial_reason = policy.select_reason(_snapshot(), _temporal(), None)
    previous = VisionKeyframe(
        sequence=4,
        captured_at=10.0,
        frame_width=640,
        frame_height=360,
        reason=KeyframeReason.INITIAL,
        scene_summary="scene",
        scene_signature=(("bottle", 1),),
    )
    event = SceneEvent(
        event_id="scene-2",
        event_type=SceneEventType.OBJECT_STARTED_MOVING,
        track_id=7,
        label="bottle",
        occurred_at=11.2,
        description="Bottle started moving.",
        confidence=0.8,
    )

    suppressed = policy.select_reason(
        _snapshot(captured_at=10.5),
        _temporal(),
        previous,
    )
    event_reason = policy.select_reason(
        _snapshot(captured_at=11.2),
        _temporal(event=event),
        previous,
    )
    forced_reason = policy.select_reason(
        _snapshot(captured_at=10.1),
        _temporal(),
        previous,
        force=True,
    )

    assert initial_reason == KeyframeReason.INITIAL
    assert suppressed is None
    assert event_reason == KeyframeReason.SCENE_EVENT
    assert forced_reason == KeyframeReason.USER_REQUEST


def test_keyframe_store_keeps_compressed_frame_only_in_memory() -> None:
    encoded: list[tuple[object, int, int]] = []

    def encoder(frame: object, maximum_edge: int, quality: int):
        encoded.append((frame, maximum_edge, quality))
        return b"compressed-jpeg", 640, 360

    store = KeyframeStore(encoder=encoder)
    frame = object()

    keyframe = store.consider(frame, _snapshot(), _temporal())

    assert keyframe is not None
    assert keyframe.reason == KeyframeReason.INITIAL
    assert keyframe.jpeg_bytes == b"compressed-jpeg"
    assert keyframe.byte_size == 15
    assert encoded == [(frame, 896, 82)]
    assert store.latest() is keyframe
    store.reset()
    assert store.latest() is None


def test_perception_service_captures_fresh_user_keyframe() -> None:
    frame = SimpleNamespace(shape=(360, 640, 3))
    manager = SimpleNamespace(
        latest_frame=lambda **kwargs: frame,
        status=lambda: SimpleNamespace(frame_sequence=42),
    )
    state_store = SceneStateStore()
    state_store.update(_snapshot(sequence=4))
    keyframes = KeyframeStore(
        encoder=lambda value, edge, quality: (b"jpeg", 640, 360)
    )
    service = PerceptionService(
        manager=manager,
        state_store=state_store,
        keyframe_store=keyframes,
    )

    keyframe = service.capture_keyframe()

    assert keyframe is not None
    assert keyframe.sequence == 42
    assert keyframe.reason == KeyframeReason.USER_REQUEST
    assert keyframe.jpeg_bytes == b"jpeg"


def test_gemma_client_sends_structured_single_keyframe_request() -> None:
    captured: dict[str, object] = {}

    def requester(endpoint: str, payload: dict, timeout: float) -> dict:
        captured.update(endpoint=endpoint, payload=payload, timeout=timeout)
        return {
            "message": {
                "content": json.dumps(
                    {
                        "answer": "A bottle is visible beside the laptop.",
                        "observations": ["One bottle is visible."],
                        "confidence": 0.87,
                        "uncertainty": "",
                    }
                )
            }
        }

    client = GemmaVisionClient(
        model="gemma3:test",
        timeout_seconds=30.0,
        requester=requester,
    )
    output = client.analyze("What is next to the laptop?", _keyframe())
    payload = captured["payload"]
    message = payload["messages"][0]

    assert output.answer.startswith("A bottle")
    assert output.confidence == 0.87
    assert captured["endpoint"] == "http://127.0.0.1:11434/api/chat"
    assert base64.b64decode(message["images"][0]) == b"jpeg-data"
    assert payload["model"] == "gemma3:test"
    assert "format" in payload
    assert payload["options"]["num_ctx"] == 2048


class _FakePerception:
    def __init__(self, keyframe: VisionKeyframe | None = None) -> None:
        self.keyframe = keyframe or _keyframe()

    def snapshot(self) -> SceneSnapshot:
        return _snapshot(sequence=self.keyframe.sequence)

    def describe_scene(self) -> str:
        return "I can see one tracked bottle."

    def describe_world(self, *, question: str = "") -> str:
        return ""

    def capture_keyframe(self) -> VisionKeyframe | None:
        return self.keyframe


class _FakeVisionClient:
    model = "gemma3:test"

    def __init__(self, *, fail: bool = False) -> None:
        self.calls = 0
        self.fail = fail

    def analyze(self, question: str, keyframe: VisionKeyframe) -> GemmaVisionOutput:
        self.calls += 1
        if self.fail:
            raise VisionModelError("offline")
        return GemmaVisionOutput(
            answer=f"Reasoned answer for {question}",
            observations=("One bottle.",),
            confidence=0.8,
        )


def test_vision_router_uses_cache_for_same_frame_and_question() -> None:
    client = _FakeVisionClient()
    router = VisionRouter(
        _FakePerception(),
        client=client,
        enabled=True,
        cache_seconds=3.0,
    )

    first = router.analyze_sync("What am I holding?")
    second = router.analyze_sync("What am I holding?")

    assert first.status == VisionReasoningStatus.READY
    assert second.used_cache is True
    assert client.calls == 1


def test_vision_router_falls_back_to_scene_state_when_gemma_is_offline() -> None:
    router = VisionRouter(
        _FakePerception(),
        client=_FakeVisionClient(fail=True),
        enabled=True,
    )

    result = router.analyze_sync("What can you see?")

    assert result.status == VisionReasoningStatus.FALLBACK
    assert result.ok is True
    assert result.answer == "I can see one tracked bottle."
    assert "offline" in result.error


def test_agent_routes_camera_reasoning_before_general_llm() -> None:
    console = Mock()
    console.send_assistant_reply.return_value = {"ok": True}
    reasoning = VisionReasoningResult(
        status=VisionReasoningStatus.READY,
        answer="You are holding a bottle, Boss.",
        model="gemma3:4b",
    )
    with (
        patch(
            "friday.src.services.agent.service.get_agent_console_service",
            return_value=console,
        ),
        patch(
            "friday.src.services.agent.service.analyze_camera_scene",
            new=AsyncMock(return_value=reasoning),
        ) as analyze,
        patch("friday.src.services.agent.service.emit_neural_transfer") as emit,
        patch("friday.src.services.agent.service._build_llm_client") as build_llm,
    ):
        result = asyncio.run(
            chat(ConsoleChatRequest(message="FRIDAY, what am I holding?"))
        )

    assert result == {"ok": True}
    analyze.assert_awaited_once()
    build_llm.assert_not_called()
    assert any(
        call.args[:2] == ("perception.vision", "reasoning.llm")
        and call.kwargs.get("event_type") == "vision.camera_reasoning.started"
        for call in emit.call_args_list
    )
    content = console.send_assistant_reply.call_args.kwargs["assistant_content"]
    assert content == "You are holding a bottle, Boss."
