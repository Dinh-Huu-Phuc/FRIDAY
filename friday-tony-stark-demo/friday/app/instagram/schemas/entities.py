"""Domain entities for the Instagram package."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class InstagramProfileEntity:
    id: str
    url: str
    label: str
    description: str = ""
    kind: str = "profile"
    metadata: dict[str, Any] = field(default_factory=dict)

@dataclass(slots=True)
class InstagramPostEntity:
    id: str
    url: str
    label: str
    description: str = ""
    kind: str = "post"
    metadata: dict[str, Any] = field(default_factory=dict)

@dataclass(slots=True)
class InstagramReelEntity:
    id: str
    url: str
    label: str
    description: str = ""
    kind: str = "reel"
    metadata: dict[str, Any] = field(default_factory=dict)

@dataclass(slots=True)
class InstagramStoryEntity:
    id: str
    url: str
    label: str
    description: str = ""
    kind: str = "story"
    metadata: dict[str, Any] = field(default_factory=dict)

@dataclass(slots=True)
class InstagramCommentEntity:
    id: str
    url: str
    label: str
    description: str = ""
    kind: str = "comment"
    metadata: dict[str, Any] = field(default_factory=dict)
