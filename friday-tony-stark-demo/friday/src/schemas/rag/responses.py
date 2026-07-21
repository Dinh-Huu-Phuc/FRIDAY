from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class RagQueryResponse(BaseModel):
    ok: bool = True
    query: str
    results: list[dict[str, Any]]


class RagIndexBuildResponse(BaseModel):
    ok: bool = True
    status: str
    message: str
