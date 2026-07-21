from __future__ import annotations

from pydantic import BaseModel, Field


class WorkspaceFileSummary(BaseModel):
    path: str
    size_bytes: int
    kind: str


class WorkspaceBlockedRule(BaseModel):
    rule: str
    reason: str


class WorkspaceIndexRequest(BaseModel):
    max_files: int = Field(default=240, ge=1, le=1000)


class WorkspaceIndexResponse(BaseModel):
    ok: bool = True
    root: str
    allowed_roots: list[str]
    blocked_rules: list[WorkspaceBlockedRule]
    files: list[WorkspaceFileSummary]
    truncated: bool = False


class WorkspaceReadRequest(BaseModel):
    path: str
    max_chars: int = Field(default=12000, ge=200, le=40000)


class WorkspaceReadResponse(BaseModel):
    ok: bool
    path: str
    content: str = ""
    truncated: bool = False
    blocked: bool = False
    reason: str | None = None


class WorkspaceSearchRequest(BaseModel):
    query: str
    max_results: int = Field(default=12, ge=1, le=40)
    max_chars_per_match: int = Field(default=420, ge=120, le=1200)


class WorkspaceSearchMatch(BaseModel):
    path: str
    line: int
    snippet: str


class WorkspaceSearchResponse(BaseModel):
    ok: bool = True
    query: str
    matches: list[WorkspaceSearchMatch]
    truncated: bool = False
