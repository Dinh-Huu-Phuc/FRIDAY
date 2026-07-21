"""Domain entities for the Facebook package."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class FacebookPageEntity:
    id: str
    url: str
    label: str
    description: str = ""
    kind: str = "page"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class FacebookPostEntity:
    id: str
    url: str
    label: str
    description: str = ""
    kind: str = "post"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class FacebookCommentEntity:
    id: str
    url: str
    label: str
    description: str = ""
    kind: str = "comment"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class FacebookReactionEntity:
    id: str
    url: str
    label: str
    description: str = ""
    kind: str = "reaction"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class FacebookMessageEntity:
    id: str
    url: str
    label: str
    sender_id: str
    recipient_id: str
    text: str = ""
    description: str = ""
    conversation_id: str = ""
    page_id: str = ""
    timestamp_ms: int = 0
    kind: str = "message"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class FacebookNotificationEntity:
    id: str
    url: str
    label: str
    event_type: str
    description: str = ""
    page_id: str = ""
    actor_id: str = ""
    timestamp_ms: int = 0
    kind: str = "notification"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class FacebookWebhookEventEntity:
    id: str
    page_id: str
    event_type: str
    timestamp_ms: int = 0
    description: str = ""
    kind: str = "webhook_event"
    metadata: dict[str, Any] = field(default_factory=dict)
