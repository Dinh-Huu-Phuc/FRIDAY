"""Domain entities for the Pinterest package."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class PinterestProfileEntity:
    id: str
    url: str
    label: str
    description: str = ""
    kind: str = "profile"
    metadata: dict[str, Any] = field(default_factory=dict)

@dataclass(slots=True)
class PinterestPinEntity:
    id: str
    url: str
    label: str
    description: str = ""
    kind: str = "pin"
    metadata: dict[str, Any] = field(default_factory=dict)

@dataclass(slots=True)
class PinterestBoardEntity:
    id: str
    url: str
    label: str
    description: str = ""
    kind: str = "board"
    metadata: dict[str, Any] = field(default_factory=dict)

@dataclass(slots=True)
class PinterestCommentEntity:
    id: str
    url: str
    label: str
    description: str = ""
    kind: str = "comment"
    metadata: dict[str, Any] = field(default_factory=dict)
