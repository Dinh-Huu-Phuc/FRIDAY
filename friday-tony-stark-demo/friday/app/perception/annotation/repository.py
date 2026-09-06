from __future__ import annotations

import hashlib
import json
import os
import shutil
import threading
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

from friday.app.perception.annotation.config import AnnotationConfig
from friday.app.perception.annotation.exceptions import (
    AnnotationConflictError,
    AnnotationNotFoundError,
)
from friday.app.perception.annotation.schemas import (
    AnnotationBox,
    AnnotationProposal,
    AnnotationStatus,
    AnnotationSummary,
)


class AnnotationRepository:
    """Persist review records and export only human-approved training samples."""

    def __init__(self, config: AnnotationConfig | None = None) -> None:
        self.config = config or AnnotationConfig.from_environment()
        self._lock = threading.RLock()

    def create_pending(
        self,
        *,
        jpeg_bytes: bytes,
        frame_width: int,
        frame_height: int,
        keyframe_sequence: int | None,
        requested_labels: tuple[str, ...],
        boxes: tuple[AnnotationBox, ...],
        source_model: str,
        source_device: str,
    ) -> AnnotationProposal:
        digest = hashlib.sha256(jpeg_bytes).hexdigest()
        with self._lock:
            existing = self._find_by_hash(digest)
            if existing is not None:
                return existing

            now = datetime.now(UTC)
            proposal_id = uuid4()
            image_path = self._relative(
                self.config.root
                / "datasets"
                / "review"
                / "images"
                / f"{proposal_id}.jpg"
            )
            proposal = AnnotationProposal(
                id=proposal_id,
                status=AnnotationStatus.PENDING,
                image_path=image_path,
                image_sha256=digest,
                frame_width=frame_width,
                frame_height=frame_height,
                keyframe_sequence=keyframe_sequence,
                requested_labels=requested_labels,
                boxes=boxes,
                source_model=source_model,
                source_device=source_device,
                created_at=now,
                updated_at=now,
            )
            image_file = self._absolute(image_path)
            record_file = self._record_path(AnnotationStatus.PENDING, proposal.id)
            self._atomic_write_bytes(image_file, jpeg_bytes)
            try:
                self._write_record(record_file, proposal)
            except Exception:
                image_file.unlink(missing_ok=True)
                raise
            return proposal

    def list(
        self,
        status: AnnotationStatus | None = None,
    ) -> list[AnnotationProposal]:
        with self._lock:
            statuses = tuple(AnnotationStatus) if status is None else (status,)
            proposals = [
                proposal
                for item_status in statuses
                for proposal in self._read_records(item_status)
            ]
        return sorted(proposals, key=lambda item: item.created_at, reverse=True)

    def find_by_image(self, jpeg_bytes: bytes) -> AnnotationProposal | None:
        digest = hashlib.sha256(jpeg_bytes).hexdigest()
        with self._lock:
            return self._find_by_hash(digest)

    def summary(self) -> AnnotationSummary:
        counts = {status: len(self.list(status)) for status in AnnotationStatus}
        return AnnotationSummary(
            pending=counts[AnnotationStatus.PENDING],
            approved=counts[AnnotationStatus.APPROVED],
            rejected=counts[AnnotationStatus.REJECTED],
        )

    def get(self, proposal_id: UUID) -> AnnotationProposal:
        with self._lock:
            for status in AnnotationStatus:
                path = self._record_path(status, proposal_id)
                if path.is_file():
                    return self._read_record(path)
        raise AnnotationNotFoundError(
            f"Annotation proposal {proposal_id} was not found."
        )

    def save_pending(self, proposal: AnnotationProposal) -> AnnotationProposal:
        if proposal.status != AnnotationStatus.PENDING:
            raise AnnotationConflictError("Only pending annotations can be edited.")
        with self._lock:
            current = self.get(proposal.id)
            if current.status != AnnotationStatus.PENDING:
                raise AnnotationConflictError("Only pending annotations can be edited.")
            self._write_record(
                self._record_path(AnnotationStatus.PENDING, proposal.id),
                proposal,
            )
        return proposal

    def approve(self, proposal: AnnotationProposal) -> AnnotationProposal:
        with self._lock:
            current = self.get(proposal.id)
            if current.status != AnnotationStatus.PENDING:
                raise AnnotationConflictError(
                    "Only pending annotations can be approved."
                )

            labels = self._register_classes(proposal.boxes)
            approved_image = (
                self.config.root
                / "datasets"
                / "approved"
                / "images"
                / f"{proposal.id}.jpg"
            )
            approved_label = (
                self.config.root
                / "datasets"
                / "approved"
                / "labels"
                / f"{proposal.id}.txt"
            )
            image_path = self._relative(approved_image)
            label_path = self._relative(approved_label)
            approved = proposal.model_copy(
                update={
                    "status": AnnotationStatus.APPROVED,
                    "image_path": image_path,
                    "label_path": label_path,
                }
            )

            source_image = self._absolute(current.image_path)
            self._atomic_copy(source_image, approved_image)
            try:
                self._atomic_write_text(
                    approved_label,
                    self._yolo_labels(approved, labels),
                )
                self._write_record(
                    self._record_path(AnnotationStatus.APPROVED, approved.id),
                    approved,
                )
                self._rebuild_coco_manifest()
            except Exception:
                approved_image.unlink(missing_ok=True)
                approved_label.unlink(missing_ok=True)
                self._record_path(AnnotationStatus.APPROVED, approved.id).unlink(
                    missing_ok=True
                )
                raise

            source_image.unlink(missing_ok=True)
            self._record_path(AnnotationStatus.PENDING, approved.id).unlink(
                missing_ok=True
            )
            return approved

    def reject(self, proposal: AnnotationProposal) -> AnnotationProposal:
        with self._lock:
            current = self.get(proposal.id)
            if current.status != AnnotationStatus.PENDING:
                raise AnnotationConflictError(
                    "Only pending annotations can be rejected."
                )
            rejected_image = (
                self.config.root
                / "datasets"
                / "rejected"
                / "images"
                / f"{proposal.id}.jpg"
            )
            rejected = proposal.model_copy(
                update={
                    "status": AnnotationStatus.REJECTED,
                    "image_path": self._relative(rejected_image),
                    "label_path": "",
                }
            )
            source_image = self._absolute(current.image_path)
            self._atomic_copy(source_image, rejected_image)
            try:
                self._write_record(
                    self._record_path(AnnotationStatus.REJECTED, rejected.id),
                    rejected,
                )
            except Exception:
                rejected_image.unlink(missing_ok=True)
                raise
            source_image.unlink(missing_ok=True)
            self._record_path(AnnotationStatus.PENDING, rejected.id).unlink(
                missing_ok=True
            )
            return rejected

    def _register_classes(self, boxes: tuple[AnnotationBox, ...]) -> list[str]:
        path = self.config.root / "annotations" / "classes.json"
        labels: list[str] = []
        if path.is_file():
            payload = json.loads(path.read_text(encoding="utf-8"))
            labels = [str(label) for label in payload.get("labels", ())]
        known = {label.casefold() for label in labels}
        for box in boxes:
            if box.label.casefold() not in known:
                labels.append(box.label)
                known.add(box.label.casefold())
        self._atomic_write_text(
            path,
            json.dumps({"version": 1, "labels": labels}, indent=2) + "\n",
        )
        return labels

    def _yolo_labels(
        self,
        proposal: AnnotationProposal,
        classes: list[str],
    ) -> str:
        class_ids = {label.casefold(): index for index, label in enumerate(classes)}
        rows: list[str] = []
        for box in proposal.boxes:
            center_x = ((box.x1 + box.x2) / 2) / proposal.frame_width
            center_y = ((box.y1 + box.y2) / 2) / proposal.frame_height
            width = (box.x2 - box.x1) / proposal.frame_width
            height = (box.y2 - box.y1) / proposal.frame_height
            rows.append(
                f"{class_ids[box.label.casefold()]} {center_x:.6f} "
                f"{center_y:.6f} {width:.6f} {height:.6f}"
            )
        return "\n".join(rows) + "\n"

    def _rebuild_coco_manifest(self) -> None:
        classes_path = self.config.root / "annotations" / "classes.json"
        payload = json.loads(classes_path.read_text(encoding="utf-8"))
        classes = [str(label) for label in payload.get("labels", ())]
        category_ids = {
            label.casefold(): index + 1 for index, label in enumerate(classes)
        }
        images: list[dict] = []
        annotations: list[dict] = []
        annotation_id = 1
        for image_id, proposal in enumerate(
            sorted(
                self._read_records(AnnotationStatus.APPROVED),
                key=lambda item: str(item.id),
            ),
            start=1,
        ):
            images.append(
                {
                    "id": image_id,
                    "file_name": proposal.image_path,
                    "width": proposal.frame_width,
                    "height": proposal.frame_height,
                }
            )
            for box in proposal.boxes:
                width = box.x2 - box.x1
                height = box.y2 - box.y1
                annotations.append(
                    {
                        "id": annotation_id,
                        "image_id": image_id,
                        "category_id": category_ids[box.label.casefold()],
                        "bbox": [box.x1, box.y1, width, height],
                        "area": width * height,
                        "iscrowd": 0,
                        "attributes": {
                            "confidence": box.confidence,
                            "source": box.source.value,
                        },
                    }
                )
                annotation_id += 1
        manifest = {
            "info": {
                "description": "FRIDAY human-approved visual annotations",
                "version": "1.0",
            },
            "images": images,
            "annotations": annotations,
            "categories": [
                {"id": index + 1, "name": label} for index, label in enumerate(classes)
            ],
        }
        self._atomic_write_text(
            self.config.root / "annotations" / "approved" / "coco.json",
            json.dumps(manifest, indent=2) + "\n",
        )

    def _find_by_hash(self, digest: str) -> AnnotationProposal | None:
        for status in AnnotationStatus:
            for proposal in self._read_records(status):
                if proposal.image_sha256 == digest:
                    return proposal
        return None

    def _read_records(self, status: AnnotationStatus) -> list[AnnotationProposal]:
        directory = self._record_path(status, None)
        if not directory.is_dir():
            return []
        return [self._read_record(path) for path in directory.glob("*.json")]

    @staticmethod
    def _read_record(path: Path) -> AnnotationProposal:
        return AnnotationProposal.model_validate_json(path.read_text(encoding="utf-8"))

    def _write_record(self, path: Path, proposal: AnnotationProposal) -> None:
        self._atomic_write_text(
            path,
            proposal.model_dump_json(indent=2) + "\n",
        )

    def _record_path(
        self,
        status: AnnotationStatus,
        proposal_id: UUID | None,
    ) -> Path:
        directory = self.config.root / "annotations" / status.value
        return directory if proposal_id is None else directory / f"{proposal_id}.json"

    def _relative(self, path: Path) -> str:
        return path.resolve().relative_to(self.config.root).as_posix()

    def _absolute(self, relative_path: str) -> Path:
        candidate = (self.config.root / relative_path).resolve()
        candidate.relative_to(self.config.root)
        return candidate

    @staticmethod
    def _atomic_write_bytes(path: Path, data: bytes) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
        try:
            temporary.write_bytes(data)
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)

    @classmethod
    def _atomic_write_text(cls, path: Path, content: str) -> None:
        cls._atomic_write_bytes(path, content.encode("utf-8"))

    @classmethod
    def _atomic_copy(cls, source: Path, destination: Path) -> None:
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_name(f".{destination.name}.{uuid4().hex}.tmp")
        try:
            shutil.copyfile(source, temporary)
            os.replace(temporary, destination)
        finally:
            temporary.unlink(missing_ok=True)
