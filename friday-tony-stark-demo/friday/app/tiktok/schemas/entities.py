"""Domain entities for the TikTok package."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class TikTokProfileEntity:
    id: str
    url: str
    label: str
    description: str = ""
    kind: str = "profile"
    metadata: dict[str, Any] = field(default_factory=dict)

@dataclass(slots=True)
class TikTokVideoEntity:
    id: str
    url: str
    label: str
    description: str = ""
    kind: str = "video"
    metadata: dict[str, Any] = field(default_factory=dict)

@dataclass(slots=True)
class TikTokShortEntity:
    id: str
    url: str
    label: str
    description: str = ""
    kind: str = "short"
    metadata: dict[str, Any] = field(default_factory=dict)

@dataclass(slots=True)
class TikTokCommentEntity:
    id: str
    url: str
    label: str
    description: str = ""
    kind: str = "comment"
    metadata: dict[str, Any] = field(default_factory=dict)
