"""Domain entities for the YouTube package."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class YouTubeChannelEntity:
    id: str
    url: str
    label: str
    description: str = ""
    kind: str = "channel"
    metadata: dict[str, Any] = field(default_factory=dict)

@dataclass(slots=True)
class YouTubeVideoEntity:
    id: str
    url: str
    label: str
    description: str = ""
    kind: str = "video"
    metadata: dict[str, Any] = field(default_factory=dict)

@dataclass(slots=True)
class YouTubePlaylistEntity:
    id: str
    url: str
    label: str
    description: str = ""
    kind: str = "playlist"
    metadata: dict[str, Any] = field(default_factory=dict)

@dataclass(slots=True)
class YouTubeCommentEntity:
    id: str
    url: str
    label: str
    description: str = ""
    kind: str = "comment"
    metadata: dict[str, Any] = field(default_factory=dict)
