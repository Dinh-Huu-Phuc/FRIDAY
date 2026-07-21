from __future__ import annotations

from pydantic import BaseModel, Field


class RuntimeStateUpdateRequest(BaseModel):
    key: str
    value: str


class AutoSleepSettingsUpdateRequest(BaseModel):
    minutes: float = Field(ge=1, le=1440)
