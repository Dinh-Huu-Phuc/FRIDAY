from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class ConsoleMessage(BaseModel):
    id: str
    role: Literal["user", "assistant", "system"]
    content: str
    timestamp: str = Field(default_factory=_now_iso)
    channel: Literal["text", "voice"] = "text"
    status: Literal["sent", "received", "pending", "error"] = "received"


class ConsoleChatRequest(BaseModel):
    message: str
    channel: Literal["text", "voice"] = "text"
    session_id: str = "browser-console"


class ConsoleState(BaseModel):
    session_id: str = "browser-console"
    messages: list[ConsoleMessage] = Field(default_factory=list)
    latest_plan: dict[str, Any] | None = None
    latest_execution: dict[str, Any] | None = None
    updated_at: str = Field(default_factory=_now_iso)


class ConsoleGreetingResponse(BaseModel):
    message: str
    generated_at: str = Field(default_factory=_now_iso)
    location: str
    weather_summary: str | None = None
    source: Literal["api", "mock"] = "api"
