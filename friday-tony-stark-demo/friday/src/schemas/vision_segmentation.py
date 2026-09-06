from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator


class SegmentationRequestBase(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class CameraSegmentationRequest(SegmentationRequestBase):
    target: str = Field(default="", max_length=100)
    precise_tracking: bool = False


class BoxSegmentationRequest(SegmentationRequestBase):
    x1: int = Field(ge=0)
    y1: int = Field(ge=0)
    x2: int = Field(ge=1)
    y2: int = Field(ge=1)
    target: str = Field(default="selected region", min_length=1, max_length=100)
    precise_tracking: bool = False

    @model_validator(mode="after")
    def validate_geometry(self) -> BoxSegmentationRequest:
        if self.x2 <= self.x1 or self.y2 <= self.y1:
            raise ValueError("The segmentation box must have positive dimensions.")
        return self


class ClearSegmentationRequest(SegmentationRequestBase):
    unload_model: bool = False
