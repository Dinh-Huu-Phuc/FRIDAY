from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator


class AnnotationRequestBase(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class CameraAnnotationProposalRequest(AnnotationRequestBase):
    labels: tuple[str, ...] = Field(min_length=1, max_length=100)


class AnnotationBoxRequest(AnnotationRequestBase):
    label: str = Field(min_length=1, max_length=100)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    x1: int = Field(ge=0)
    y1: int = Field(ge=0)
    x2: int = Field(ge=1)
    y2: int = Field(ge=1)

    @model_validator(mode="after")
    def validate_geometry(self) -> AnnotationBoxRequest:
        if self.x2 <= self.x1 or self.y2 <= self.y1:
            raise ValueError("Annotation boxes must have a positive width and height.")
        return self


class AnnotationCorrectionRequest(AnnotationRequestBase):
    boxes: tuple[AnnotationBoxRequest, ...] | None = None
    review_note: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def require_a_change(self) -> AnnotationCorrectionRequest:
        if self.boxes is None and self.review_note is None:
            raise ValueError("Supply boxes or a review note.")
        return self


class AnnotationApprovalRequest(AnnotationRequestBase):
    review_note: str | None = Field(default=None, max_length=1000)


class AnnotationRejectionRequest(AnnotationRequestBase):
    reason: str = Field(min_length=1, max_length=500)
