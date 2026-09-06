from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from threading import Lock
from uuid import UUID

from friday.app.perception.annotation.config import AnnotationConfig
from friday.app.perception.annotation.exceptions import (
    AnnotationConflictError,
    AnnotationUnavailableError,
    AnnotationValidationError,
)
from friday.app.perception.annotation.repository import AnnotationRepository
from friday.app.perception.annotation.schemas import (
    AnnotationBox,
    AnnotationProposal,
    AnnotationSource,
    AnnotationStatus,
    AnnotationSummary,
)
from friday.app.perception.detection.grounding import (
    GroundingDinoDetector,
    GroundingModelError,
)
from friday.app.perception.reasoning import KeyframeReason, VisionKeyframe
from friday.app.perception.service import get_perception_service


class AnnotationService:
    """Generate Grounding DINO proposals while reserving approval for a human."""

    def __init__(
        self,
        repository: AnnotationRepository | None = None,
        *,
        detector: GroundingDinoDetector | None = None,
        perception_service=None,
        config: AnnotationConfig | None = None,
    ) -> None:
        self.config = config or AnnotationConfig.from_environment()
        self.repository = repository or AnnotationRepository(self.config)
        self._detector = detector or GroundingDinoDetector()
        self._perception = perception_service

    def propose_from_camera(self, labels: tuple[str, ...]) -> AnnotationProposal:
        perception = self._perception or get_perception_service()
        keyframe = perception.capture_keyframe()
        if keyframe is None or not keyframe.jpeg_bytes:
            raise AnnotationUnavailableError(
                "Open the FRIDAY Camera Window before creating an annotation proposal."
            )
        return self.propose_from_keyframe(keyframe, labels)

    def propose_from_image(
        self,
        image_path: str | Path,
        labels: tuple[str, ...],
    ) -> AnnotationProposal:
        path = Path(image_path).expanduser().resolve()
        if not path.is_file():
            raise AnnotationValidationError(f"Image file does not exist: {path}")
        try:
            import cv2  # type: ignore
        except ImportError as exc:
            raise AnnotationUnavailableError(
                "opencv-python is required to prepare annotation images."
            ) from exc
        frame = cv2.imread(str(path))
        if frame is None or not hasattr(frame, "shape"):
            raise AnnotationValidationError(f"Could not decode image: {path}")
        height, width = (int(value) for value in frame.shape[:2])
        ok, encoded = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 92])
        if not ok:
            raise AnnotationValidationError(f"Could not encode image: {path}")
        keyframe = VisionKeyframe(
            sequence=0,
            captured_at=path.stat().st_mtime,
            frame_width=width,
            frame_height=height,
            reason=KeyframeReason.USER_REQUEST,
            scene_summary=f"Annotation source image: {path.name}",
            scene_signature=(),
            jpeg_bytes=bytes(encoded),
        )
        return self.propose_from_keyframe(keyframe, labels)

    def propose_from_keyframe(
        self,
        keyframe: VisionKeyframe,
        labels: tuple[str, ...],
    ) -> AnnotationProposal:
        normalized_labels = self._normalize_labels(labels)
        existing = self.repository.find_by_image(keyframe.jpeg_bytes)
        if existing is not None:
            return existing
        grounding_prompts = tuple(
            self._grounding_prompt(label) for label in normalized_labels
        )
        try:
            matches = self._detector.detect_many(
                keyframe,
                grounding_prompts,
                max_results=max(10, len(normalized_labels) * 10),
            )
        except GroundingModelError as exc:
            raise AnnotationUnavailableError(str(exc)) from exc
        boxes = tuple(
            box
            for match in matches
            if (
                box := self._grounding_box(
                    self._canonical_match_label(match.label, normalized_labels),
                    match.confidence,
                    match.box.x1,
                    match.box.y1,
                    match.box.x2,
                    match.box.y2,
                    keyframe.frame_width,
                    keyframe.frame_height,
                )
            )
            is not None
        )
        return self.repository.create_pending(
            jpeg_bytes=keyframe.jpeg_bytes,
            frame_width=keyframe.frame_width,
            frame_height=keyframe.frame_height,
            keyframe_sequence=keyframe.sequence,
            requested_labels=normalized_labels,
            boxes=boxes,
            source_model=self._detector.model,
            source_device=self._detector.device,
        )

    def list(
        self,
        status: AnnotationStatus | None = None,
    ) -> list[AnnotationProposal]:
        return self.repository.list(status)

    def summary(self) -> AnnotationSummary:
        return self.repository.summary()

    def get(self, proposal_id: UUID) -> AnnotationProposal:
        return self.repository.get(proposal_id)

    def correct(
        self,
        proposal_id: UUID,
        *,
        boxes: tuple[AnnotationBox, ...] | None = None,
        review_note: str | None = None,
    ) -> AnnotationProposal:
        proposal = self.repository.get(proposal_id)
        if proposal.status != AnnotationStatus.PENDING:
            raise AnnotationConflictError("Only pending annotations can be edited.")
        updates: dict = {
            "updated_at": datetime.now(UTC),
            "revision": proposal.revision + 1,
        }
        if boxes is not None:
            normalized_boxes = tuple(
                box.model_copy(
                    update={
                        "label": self._normalize_label(box.label),
                        "source": AnnotationSource.HUMAN,
                    }
                )
                for box in boxes
            )
            self._validate_box_bounds(
                normalized_boxes,
                proposal.frame_width,
                proposal.frame_height,
            )
            updates["boxes"] = normalized_boxes
        if review_note is not None:
            updates["review_note"] = review_note.strip()[:1000]
        if boxes is None and review_note is None:
            raise AnnotationValidationError("Supply boxes or a review note to edit.")
        return self.repository.save_pending(proposal.model_copy(update=updates))

    def approve(
        self,
        proposal_id: UUID,
        *,
        review_note: str | None = None,
    ) -> AnnotationProposal:
        proposal = self.repository.get(proposal_id)
        if proposal.status != AnnotationStatus.PENDING:
            raise AnnotationConflictError("Only pending annotations can be approved.")
        if not proposal.boxes:
            raise AnnotationValidationError(
                "At least one reviewed box is required before approval."
            )
        self._validate_box_bounds(
            proposal.boxes,
            proposal.frame_width,
            proposal.frame_height,
        )
        now = datetime.now(UTC)
        reviewed = proposal.model_copy(
            update={
                "reviewed_at": now,
                "updated_at": now,
                "review_note": (
                    proposal.review_note
                    if review_note is None
                    else review_note.strip()[:1000]
                ),
                "revision": proposal.revision + 1,
            }
        )
        return self.repository.approve(reviewed)

    def reject(self, proposal_id: UUID, reason: str) -> AnnotationProposal:
        proposal = self.repository.get(proposal_id)
        if proposal.status != AnnotationStatus.PENDING:
            raise AnnotationConflictError("Only pending annotations can be rejected.")
        cleaned_reason = " ".join(reason.strip().split())[:500]
        if not cleaned_reason:
            raise AnnotationValidationError("A rejection reason is required.")
        now = datetime.now(UTC)
        rejected = proposal.model_copy(
            update={
                "reviewed_at": now,
                "updated_at": now,
                "rejection_reason": cleaned_reason,
                "revision": proposal.revision + 1,
            }
        )
        return self.repository.reject(rejected)

    def _normalize_labels(self, labels: tuple[str, ...]) -> tuple[str, ...]:
        normalized: list[str] = []
        known: set[str] = set()
        for value in labels:
            label = self._normalize_label(value)
            if label.casefold() not in known:
                normalized.append(label)
                known.add(label.casefold())
        if not normalized:
            raise AnnotationValidationError("At least one object label is required.")
        if len(normalized) > self.config.max_labels:
            raise AnnotationValidationError(
                f"At most {self.config.max_labels} labels may be requested at once."
            )
        return tuple(normalized)

    @staticmethod
    def _grounding_prompt(label: str) -> str:
        words = label.split()
        if not words or words[0] in {"a", "an", "the", "some"}:
            return label
        paired_objects = {"binoculars", "glasses", "headphones", "scissors"}
        if words[-1] in paired_objects:
            return f"a pair of {label}"
        article = "an" if label[0] in "aeiou" else "a"
        return f"{article} {label}"

    @classmethod
    def _canonical_match_label(
        cls,
        detected_label: str,
        requested_labels: tuple[str, ...],
    ) -> str:
        detected_tokens = cls._label_tokens(detected_label)
        best_label = ""
        best_score = 0.0
        for label in requested_labels:
            requested_tokens = cls._label_tokens(label)
            union = detected_tokens | requested_tokens
            score = len(detected_tokens & requested_tokens) / len(union) if union else 0
            if score > best_score:
                best_label = label
                best_score = score
        return best_label or cls._normalize_label(detected_label)

    @staticmethod
    def _label_tokens(label: str) -> set[str]:
        ignored = {"a", "an", "the", "some", "pair", "of"}
        return {
            token
            for token in "".join(
                character if character.isalnum() else " "
                for character in label.casefold()
            ).split()
            if token not in ignored
        }

    @staticmethod
    def _normalize_label(value: str) -> str:
        label = " ".join(str(value or "").strip().split()).casefold()[:100]
        if not label:
            raise AnnotationValidationError("Annotation labels cannot be empty.")
        return label

    @staticmethod
    def _grounding_box(
        label: str,
        confidence: float,
        x1: int,
        y1: int,
        x2: int,
        y2: int,
        frame_width: int,
        frame_height: int,
    ) -> AnnotationBox | None:
        left = max(0, min(frame_width - 1, x1))
        top = max(0, min(frame_height - 1, y1))
        right = max(1, min(frame_width, x2))
        bottom = max(1, min(frame_height, y2))
        if right <= left or bottom <= top:
            return None
        return AnnotationBox(
            label=" ".join(label.strip().split()).casefold()[:100],
            confidence=max(0.0, min(1.0, confidence)),
            x1=left,
            y1=top,
            x2=right,
            y2=bottom,
            source=AnnotationSource.GROUNDING_DINO,
        )

    @staticmethod
    def _validate_box_bounds(
        boxes: tuple[AnnotationBox, ...],
        frame_width: int,
        frame_height: int,
    ) -> None:
        for box in boxes:
            if box.x2 > frame_width or box.y2 > frame_height:
                raise AnnotationValidationError(
                    f"Box {box.id} exceeds the {frame_width}x{frame_height} image."
                )


_ANNOTATION_SERVICE: AnnotationService | None = None
_ANNOTATION_SERVICE_LOCK = Lock()


def get_annotation_service() -> AnnotationService:
    global _ANNOTATION_SERVICE
    if _ANNOTATION_SERVICE is None:
        with _ANNOTATION_SERVICE_LOCK:
            if _ANNOTATION_SERVICE is None:
                _ANNOTATION_SERVICE = AnnotationService()
    return _ANNOTATION_SERVICE
