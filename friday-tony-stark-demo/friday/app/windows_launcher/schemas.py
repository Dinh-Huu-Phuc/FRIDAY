"""Schemas for discovering and launching local Windows apps."""

from __future__ import annotations

from pydantic import BaseModel, Field


class AppMatch(BaseModel):
    name: str
    source: str
    score: float = 0.0
    app_id: str | None = None
    path: str | None = None
    kind: str = "app"


class AppSearchRequest(BaseModel):
    query: str
    limit: int = Field(default=8, ge=1, le=25)


class AppOpenRequest(BaseModel):
    query: str | None = None
    app_id: str | None = None
    path: str | None = None
    min_score: float = Field(default=0.55, ge=0.0, le=1.0)


class AppSearchResponse(BaseModel):
    ok: bool = True
    query: str
    items: list[AppMatch] = Field(default_factory=list)
    message: str


class AppLaunchResponse(BaseModel):
    ok: bool
    message: str
    selected: AppMatch | None = None
    candidates: list[AppMatch] = Field(default_factory=list)
