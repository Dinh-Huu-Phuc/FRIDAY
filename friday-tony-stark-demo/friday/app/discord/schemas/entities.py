"""Domain entities for the Discord package."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class DiscordGuildEntity:
    id: str
    url: str
    label: str
    description: str = ""
    kind: str = "guild"
    metadata: dict[str, Any] = field(default_factory=dict)

@dataclass(slots=True)
class DiscordMessageEntity:
    id: str
    url: str
    label: str
    description: str = ""
    kind: str = "message"
    metadata: dict[str, Any] = field(default_factory=dict)

@dataclass(slots=True)
class DiscordChannelEntity:
    id: str
    url: str
    label: str
    description: str = ""
    kind: str = "channel"
    metadata: dict[str, Any] = field(default_factory=dict)

@dataclass(slots=True)
class DiscordThreadEntity:
    id: str
    url: str
    label: str
    description: str = ""
    kind: str = "thread"
    metadata: dict[str, Any] = field(default_factory=dict)
