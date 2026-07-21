from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


AllowedScope = Literal[
    "agent:chat",
    "rag:query",
    "computer:run",
    "runtime:read",
    "sse:connect",
    "api_keys:manage",
]


class ApiKeyCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    scopes: list[AllowedScope] = Field(default_factory=list)
    environment: Literal["dev", "prod", "local"] = "local"
    expires_at: datetime | None = None
    rate_limit_per_minute: int | None = Field(default=None, ge=1)
    token_limit_daily: int | None = Field(default=None, ge=1)
    notes: str | None = None


class ApiKeyVerifyRequest(BaseModel):
    api_key: str = Field(min_length=1)
