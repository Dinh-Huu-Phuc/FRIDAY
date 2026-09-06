from __future__ import annotations

from datetime import datetime
from enum import Enum
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator


class AnnotationStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class AnnotationSource(str, Enum):
    GROUNDING_DINO = "grounding_dino"
    HUMAN = "human"


class AnnotationBox(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)

    id: UUID = Field(default_factory=uuid4)
    label: str = Field(min_length=1, max_length=100)
    confidence: float = Field(ge=0.0, le=1.0)
    x1: int = Field(ge=0)
    y1: int = Field(ge=0)
    x2: int = Field(ge=1)
    y2: int = Field(ge=1)
    source: AnnotationSource = AnnotationSource.GROUNDING_DINO

    @model_validator(mode="after")
    def validate_geometry(self) -> AnnotationBox:
        if self.x2 <= self.x1 or self.y2 <= self.y1:
            raise ValueError("Annotation boxes must have a positive width and height.")
        return self


class AnnotationProposal(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: UUID
    status: AnnotationStatus
    image_path: str
    label_path: str = ""
    image_sha256: str = Field(min_length=64, max_length=64)
    frame_width: int = Field(gt=0)
    frame_height: int = Field(gt=0)
    keyframe_sequence: int | None = None
    requested_labels: tuple[str, ...]
    boxes: tuple[AnnotationBox, ...] = ()
    source_model: str
    source_device: str = ""
    created_at: datetime
    updated_at: datetime
    reviewed_at: datetime | None = None
    review_note: str = ""
    rejection_reason: str = ""
    revision: int = Field(default=1, ge=1)


class AnnotationSummary(BaseModel):
    pending: int = 0
    approved: int = 0
    rejected: int = 0

    @property
    def total(self) -> int:
        return self.pending + self.approved + self.rejected
