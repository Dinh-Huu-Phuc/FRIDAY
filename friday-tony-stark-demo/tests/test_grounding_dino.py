from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from friday.app.agent_console.schemas import ConsoleChatRequest
from friday.app.perception.detection import (
    BoundingBox,
    SceneSnapshot,
    TrackedObject,
)
from friday.app.perception.detection.grounding import (
    GroundingDinoConfig,
    GroundingDinoDetector,
    GroundingMatch,
    GroundingModelError,
    GroundingResult,
    GroundingStatus,
    OpenVocabularyService,
    match_grounding_intent,
)
from friday.app.perception.detection.grounding.grounding_dino import _select_device
from friday.app.perception.reasoning import KeyframeReason, VisionKeyframe
from friday.app.perception.window import CameraWindowAction, match_camera_window_intent
from friday.src.services.agent.service import chat


def _keyframe(sequence: int = 8) -> VisionKeyframe:
    return VisionKeyframe(
        sequence=sequence,
        captured_at=1.0,
        frame_width=640,
        frame_height=360,
        reason=KeyframeReason.USER_REQUEST,
        scene_summary="One tracked person.",
        scene_signature=(("person", 1),),
        jpeg_bytes=b"jpeg",
    )


class _FakePerception:
    def __init__(self, *, objects: tuple[TrackedObject, ...] = ()) -> None:
        self._snapshot = SceneSnapshot(
            sequence=8,
            captured_at=1.0,
            frame_width=640,
            frame_height=360,
            objects=objects,
            status="ready",
            model_name="yolo26n",
        )
        self.published: GroundingResult | None = None

    def snapshot(self) -> SceneSnapshot:
        return self._snapshot

    def capture_keyframe(self) -> VisionKeyframe:
        return _keyframe(self._snapshot.sequence)

    def set_grounding_result(self, result: GroundingResult) -> None:
        self.published = result


class _FakeGroundingDetector:
    model = "IDEA-Research/grounding-dino-tiny"
    device = "cpu"

    def __init__(self, *, fail: bool = False) -> None:
        self.calls = 0
        self.fail = fail

    def detect(
        self,
        keyframe: VisionKeyframe | bytes,
        queries: tuple[str, ...],
        **_options,
    ) -> tuple[GroundingMatch, ...]:
        del keyframe
        self.calls += 1
        if self.fail:
            raise GroundingModelError("model unavailable")
        return (
            GroundingMatch(
                label=queries[0],
                confidence=0.82,
                box=BoundingBox(420, 90, 580, 260),
            ),
        )


def test_grounding_intent_requires_an_explicit_camera_or_visual_phrase() -> None:
    direct = match_grounding_intent(
        "FRIDAY, find the medicine bottle with a blue cap in the camera."
    )
    visual = match_grounding_intent("FRIDAY, visually find my red screwdriver.")

    assert direct.matched is True
    assert direct.query == "medicine bottle with a blue cap"
    assert visual.matched is True
    assert visual.query == "red screwdriver"
    assert match_grounding_intent("Find today's Bitcoin price").matched is False
    assert (
        match_camera_window_intent("Locate my glasses using the webcam").action
        == CameraWindowAction.LOCATE
    )


def test_grounding_detector_loads_the_optional_backend_only_once() -> None:
    loaded: list[tuple[str, str, bool, int]] = []
    backend = _FakeGroundingDetector()

    def loader(model: str, device: str, local_only: bool, minimum_vram: int):
        loaded.append((model, device, local_only, minimum_vram))
        return backend

    config = GroundingDinoConfig(
        model_id="grounding-test",
        device="cpu",
        local_files_only=True,
        minimum_cuda_vram_mb=6144,
        box_threshold=0.35,
        text_threshold=0.25,
        max_results=5,
    )
    detector = GroundingDinoDetector(config, backend_loader=loader)

    detector.detect(_keyframe(), "blue medicine bottle")
    detector.detect(_keyframe(), "red screwdriver")

    assert loaded == [("grounding-test", "cpu", True, 6144)]
    assert backend.calls == 2


def test_grounding_detector_batches_multiple_annotation_labels() -> None:
    backend = _FakeGroundingDetector()
    detector = GroundingDinoDetector(
        GroundingDinoConfig(
            model_id="grounding-test",
            device="cpu",
            local_files_only=True,
            minimum_cuda_vram_mb=6144,
            box_threshold=0.35,
            text_threshold=0.25,
            max_results=5,
        ),
        backend_loader=lambda *_args: backend,
    )

    matches = detector.detect_many(
        _keyframe(),
        ("medicine bottle", "red screwdriver"),
        max_results=20,
    )

    assert backend.calls == 1
    assert matches[0].label == "medicine bottle"


def test_auto_device_keeps_a_four_gigabyte_gpu_on_cpu() -> None:
    cuda = SimpleNamespace(
        is_available=lambda: True,
        get_device_properties=lambda _index: SimpleNamespace(
            total_memory=4 * 1024 * 1024 * 1024
        ),
    )
    torch = SimpleNamespace(cuda=cuda)

    assert _select_device(torch, "auto", 6144) == "cpu"
    assert _select_device(torch, "cuda", 6144) == "cuda"


def test_known_simple_object_uses_primary_detector_without_grounding_dino() -> None:
    bottle = TrackedObject(
        track_id=4,
        class_id=39,
        label="bottle",
        confidence=0.91,
        box=BoundingBox(20, 60, 160, 310),
    )
    perception = _FakePerception(objects=(bottle,))
    detector = _FakeGroundingDetector()
    service = OpenVocabularyService(perception, detector=detector, enabled=True)

    result = service.locate_sync("bottle")

    assert result.status == GroundingStatus.READY
    assert result.provider == "primary_detector"
    assert result.matches[0].box == bottle.box
    assert detector.calls == 0
    assert perception.published == result


def test_unfamiliar_object_runs_grounding_dino_and_caches_same_keyframe() -> None:
    perception = _FakePerception()
    detector = _FakeGroundingDetector()
    service = OpenVocabularyService(
        perception,
        detector=detector,
        enabled=True,
        cache_seconds=30,
    )

    first = service.locate_sync("medicine bottle with a blue cap")
    second = service.locate_sync("medicine bottle with a blue cap")

    assert first.status == GroundingStatus.READY
    assert first.provider == "grounding_dino"
    assert "middle-right" in first.answer
    assert second.used_cache is True
    assert detector.calls == 1
    assert perception.published == second


def test_grounding_dependency_failure_returns_an_honest_unavailable_result() -> None:
    service = OpenVocabularyService(
        _FakePerception(),
        detector=_FakeGroundingDetector(fail=True),
        enabled=True,
    )

    result = service.locate_sync("unfamiliar device")

    assert result.status == GroundingStatus.UNAVAILABLE
    assert result.ok is False
    assert "needs attention" in result.answer
    assert result.error == "model unavailable"


def test_agent_routes_camera_location_before_general_llm() -> None:
    console = Mock()
    console.send_assistant_reply.return_value = {"ok": True}
    grounding = GroundingResult(
        status=GroundingStatus.READY,
        query="red screwdriver",
        answer="I found the red screwdriver on the right, Boss.",
    )
    with (
        patch(
            "friday.src.services.agent.service.get_agent_console_service",
            return_value=console,
        ),
        patch(
            "friday.src.services.agent.service.locate_camera_object",
            new=AsyncMock(return_value=grounding),
        ) as locate,
        patch("friday.src.services.agent.service.emit_neural_activity") as activity,
        patch("friday.src.services.agent.service._build_llm_client") as build_llm,
    ):
        result = asyncio.run(
            chat(
                ConsoleChatRequest(
                    message="FRIDAY, locate my red screwdriver using the webcam."
                )
            )
        )

    assert result == {"ok": True}
    locate.assert_awaited_once_with("red screwdriver")
    build_llm.assert_not_called()
    assert any(
        call.kwargs.get("event_type") == "vision.open_vocabulary.started"
        for call in activity.call_args_list
    )
    content = console.send_assistant_reply.call_args.kwargs["assistant_content"]
    assert content == grounding.answer
