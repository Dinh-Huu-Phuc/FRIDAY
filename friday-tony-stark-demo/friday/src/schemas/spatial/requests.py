from __future__ import annotations

from pydantic import BaseModel, Field


class SpatialStartRequest(BaseModel):
    mode: str = Field(default="hand_tracking", min_length=1, max_length=64)
    camera_index: int | None = Field(default=None, ge=0)


class SpatialModeRequest(BaseModel):
    mode: str = Field(min_length=1, max_length=64)
