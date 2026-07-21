"""Domain entities for the X package."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class XAccountEntity:
    id: str
    url: str
    label: str
    description: str = ""
    kind: str = "account"
    metadata: dict[str, Any] = field(default_factory=dict)

@dataclass(slots=True)
class XTweetEntity:
    id: str
    url: str
    label: str
    description: str = ""
    kind: str = "tweet"
    metadata: dict[str, Any] = field(default_factory=dict)

@dataclass(slots=True)
class XThreadEntity:
    id: str
    url: str
    label: str
    description: str = ""
    kind: str = "thread"
    metadata: dict[str, Any] = field(default_factory=dict)

@dataclass(slots=True)
class XReplyEntity:
    id: str
    url: str
    label: str
    description: str = ""
    kind: str = "reply"
    metadata: dict[str, Any] = field(default_factory=dict)
