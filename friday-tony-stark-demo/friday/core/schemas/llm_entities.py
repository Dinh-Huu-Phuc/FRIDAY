from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal


ChatRole = Literal["system", "user", "assistant", "tool"]


@dataclass(slots=True)
class ChatMessage:
    role: ChatRole
    content: str
    name: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        if self.name is None:
            payload.pop("name", None)
        return payload


@dataclass(slots=True)
class LLMRequest:
    messages: list[ChatMessage]
    model: str
    temperature: float = 0.2
    max_tokens: int | None = None
    stream: bool = False


@dataclass(slots=True)
class LLMResponse:
    content: str
    model: str
    provider: str
    raw: dict[str, Any] = field(default_factory=dict)
