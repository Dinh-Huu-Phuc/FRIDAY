"""Domain entities for the Telegram package."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class TelegramChatEntity:
    id: str
    url: str
    label: str
    description: str = ""
    kind: str = "chat"
    metadata: dict[str, Any] = field(default_factory=dict)

@dataclass(slots=True)
class TelegramMessageEntity:
    id: str
    url: str
    label: str
    description: str = ""
    kind: str = "message"
    metadata: dict[str, Any] = field(default_factory=dict)

@dataclass(slots=True)
class TelegramChannelEntity:
    id: str
    url: str
    label: str
    description: str = ""
    kind: str = "channel"
    metadata: dict[str, Any] = field(default_factory=dict)
