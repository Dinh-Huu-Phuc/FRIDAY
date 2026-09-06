from __future__ import annotations

import json
from pathlib import Path

import pytest

from friday.app.perception.annotation import (
    AnnotationBox,
    AnnotationConfig,
    AnnotationConflictError,
    AnnotationRepository,
    AnnotationService,
    AnnotationSource,
    AnnotationStatus,
    AnnotationValidationError,
)
from friday.app.perception.annotation.cli import _propose_camera_via_api
from friday.app.perception.detection import BoundingBox
from friday.app.perception.detection.grounding import GroundingMatch
from friday.app.perception.reasoning import KeyframeReason, VisionKeyframe
from friday.src.router.api_router import api_router


class _FakeGroundingDetector:
    model = "grounding-test"
    device = "cpu"

    def __init__(self) -> None:
        self.calls: list[tuple[str, ...]] = []

    def detect_many(
        self,
        _keyframe: VisionKeyframe,
        labels: tuple[str, ...],
        **_options,
    ) -> tuple[GroundingMatch, ...]:
        self.calls.append(labels)
        return (
            GroundingMatch(
                label=labels[0],
                confidence=0.82,
                box=BoundingBox(10, 20, 110, 120),
            ),
        )


def _keyframe(jpeg_bytes: bytes = b"test-jpeg") -> VisionKeyframe:
    return VisionKeyframe(
        sequence=17,
        captured_at=1.0,
        frame_width=200,
        frame_height=160,
        reason=KeyframeReason.USER_REQUEST,
        scene_summary="Test scene",
        scene_signature=(),
        jpeg_bytes=jpeg_bytes,
    )


def _service(tmp_path: Path) -> tuple[AnnotationService, _FakeGroundingDetector]:
    config = AnnotationConfig(root=tmp_path / "vision", max_labels=20)
    detector = _FakeGroundingDetector()
    repository = AnnotationRepository(config)
    return (
        AnnotationService(
            repository,
            detector=detector,
            config=config,
        ),
        detector,
    )


def test_grounding_proposal_stays_pending_and_removes_duplicate_frames(
    tmp_path: Path,
) -> None:
    service, detector = _service(tmp_path)

    first = service.propose_from_keyframe(
        _keyframe(),
        ("Medicine Bottle", "medicine bottle", "red screwdriver"),
    )
    duplicate = service.propose_from_keyframe(
        _keyframe(),
        ("medicine bottle",),
    )

    assert first.status == AnnotationStatus.PENDING
    assert first.requested_labels == ("medicine bottle", "red screwdriver")
    assert first.boxes[0].label == "medicine bottle"
    assert first.boxes[0].source == AnnotationSource.GROUNDING_DINO
    assert duplicate.id == first.id
    assert detector.calls == [("a medicine bottle", "a red screwdriver")]
    assert service.summary().pending == 1
    assert not (tmp_path / "vision" / "datasets" / "approved").exists()


def test_annotation_prompts_pair_objects_but_keep_canonical_class_names(
    tmp_path: Path,
) -> None:
    service, detector = _service(tmp_path)

    proposal = service.propose_from_keyframe(
        _keyframe(b"headphones-jpeg"),
        ("person", "headphones"),
    )

    assert detector.calls == [("a person", "a pair of headphones")]
    assert proposal.boxes[0].label == "person"


def test_human_correction_and_approval_export_yolo_and_coco(tmp_path: Path) -> None:
    service, _detector = _service(tmp_path)
    proposal = service.propose_from_keyframe(_keyframe(), ("bottle",))
    corrected = service.correct(
        proposal.id,
        boxes=(
            AnnotationBox(
                label="Medicine Bottle",
                confidence=1.0,
                x1=20,
                y1=20,
                x2=120,
                y2=100,
                source=AnnotationSource.HUMAN,
            ),
        ),
        review_note="Bounding box checked manually.",
    )
    approved = service.approve(corrected.id)

    root = tmp_path / "vision"
    assert corrected.boxes[0].label == "medicine bottle"
    assert corrected.boxes[0].source == AnnotationSource.HUMAN
    assert approved.status == AnnotationStatus.APPROVED
    assert approved.reviewed_at is not None
    assert not (root / "annotations" / "pending" / f"{proposal.id}.json").exists()
    yolo = (root / approved.label_path).read_text(encoding="utf-8")
    assert yolo == "0 0.350000 0.375000 0.500000 0.500000\n"

    coco = json.loads(
        (root / "annotations" / "approved" / "coco.json").read_text(encoding="utf-8")
    )
    assert coco["categories"] == [{"id": 1, "name": "medicine bottle"}]
    assert coco["annotations"][0]["bbox"] == [20, 20, 100, 80]
    assert coco["annotations"][0]["attributes"]["source"] == "human"
    with pytest.raises(AnnotationConflictError):
        service.approve(approved.id)


def test_rejected_annotations_never_enter_the_training_dataset(tmp_path: Path) -> None:
    service, _detector = _service(tmp_path)
    proposal = service.propose_from_keyframe(_keyframe(), ("unknown object",))

    rejected = service.reject(proposal.id, "The proposed label is incorrect.")

    root = tmp_path / "vision"
    assert rejected.status == AnnotationStatus.REJECTED
    assert rejected.rejection_reason == "The proposed label is incorrect."
    assert (root / rejected.image_path).is_file()
    assert not (root / "datasets" / "approved").exists()
    with pytest.raises(AnnotationConflictError):
        service.approve(rejected.id)


def test_box_bounds_and_empty_approval_are_rejected(tmp_path: Path) -> None:
    service, detector = _service(tmp_path)
    detector.detect_many = lambda *_args, **_kwargs: ()
    proposal = service.propose_from_keyframe(_keyframe(), ("bottle",))

    with pytest.raises(AnnotationValidationError, match="At least one"):
        service.approve(proposal.id)
    with pytest.raises(AnnotationValidationError, match="exceeds"):
        service.correct(
            proposal.id,
            boxes=(
                AnnotationBox(
                    label="bottle",
                    confidence=1.0,
                    x1=0,
                    y1=0,
                    x2=201,
                    y2=100,
                    source=AnnotationSource.HUMAN,
                ),
            ),
        )


def test_annotation_api_routes_are_registered() -> None:
    paths = {route.path for route in api_router.routes}

    assert "/vision-annotations" in paths
    assert "/vision-annotations/proposals/camera" in paths
    assert "/vision-annotations/{proposal_id}/approve" in paths
    assert "/vision-annotations/{proposal_id}/reject" in paths


def test_camera_cli_uses_the_running_local_api(monkeypatch) -> None:
    captured = {}

    class _Response:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        @staticmethod
        def read() -> bytes:
            return b'{"status":"pending"}'

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["body"] = json.loads(request.data)
        captured["timeout"] = timeout
        return _Response()

    monkeypatch.setattr(
        "friday.app.perception.annotation.cli.urlopen",
        fake_urlopen,
    )

    result = _propose_camera_via_api(
        "http://127.0.0.1:8001/",
        ["medicine bottle"],
    )

    assert result == {"status": "pending"}
    assert captured["url"].endswith("/api/v1/vision-annotations/proposals/camera")
    assert captured["body"] == {"labels": ["medicine bottle"]}
    assert captured["timeout"] == 180
