from __future__ import annotations

from pydantic import BaseModel, Field


class RagQueryRequest(BaseModel):
    query: str = Field(min_length=1)
    top_k: int = Field(default=5, ge=1, le=50)


class RagIndexBuildRequest(BaseModel):
    source: str | None = None
    force: bool = False
