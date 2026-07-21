from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from friday.src.common.utils import utc_now


class RuntimeStateResponse(BaseModel):
    ok: bool = True
    state: dict[str, Any] = Field(default_factory=dict)
    generated_at: datetime = Field(default_factory=utc_now)


class RuntimeStatusResponse(BaseModel):
    ok: bool = True
    status: str = "running"
    generated_at: datetime = Field(default_factory=utc_now)
