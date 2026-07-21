"""Domain entities for the Reddit package."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class RedditSubredditEntity:
    id: str
    url: str
    label: str
    description: str = ""
    kind: str = "subreddit"
    metadata: dict[str, Any] = field(default_factory=dict)

@dataclass(slots=True)
class RedditPostEntity:
    id: str
    url: str
    label: str
    description: str = ""
    kind: str = "post"
    metadata: dict[str, Any] = field(default_factory=dict)

@dataclass(slots=True)
class RedditCommentEntity:
    id: str
    url: str
    label: str
    description: str = ""
    kind: str = "comment"
    metadata: dict[str, Any] = field(default_factory=dict)

@dataclass(slots=True)
class RedditThreadEntity:
    id: str
    url: str
    label: str
    description: str = ""
    kind: str = "thread"
    metadata: dict[str, Any] = field(default_factory=dict)
