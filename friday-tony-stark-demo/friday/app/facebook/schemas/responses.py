"""Response models for the Facebook package."""

from __future__ import annotations

from dataclasses import dataclass, field

from friday.app.facebook.schemas.entities import (
    FacebookMessageEntity,
    FacebookNotificationEntity,
    FacebookPageEntity,
    FacebookPostEntity,
    FacebookWebhookEventEntity,
)


@dataclass(slots=True)
class OpenPlatformResponse:
    platform: str
    url: str
    message: str
    opened: bool


@dataclass(slots=True)
class ProfileResponse:
    platform: str
    profile: FacebookPageEntity


@dataclass(slots=True)
class ContentSearchResponse:
    platform: str
    query: str
    items: list[FacebookPostEntity] = field(default_factory=list)


@dataclass(slots=True)
class ContentDetailResponse:
    platform: str
    item: FacebookPostEntity


@dataclass(slots=True)
class PublishContentResponse:
    platform: str
    item: FacebookPostEntity
    status: str = "queued"


@dataclass(slots=True)
class WebhookVerificationResponse:
    verified: bool
    challenge: str = ""
    message: str = ""


@dataclass(slots=True)
class WebhookIngestResponse:
    platform: str
    accepted: bool
    stored_event_count: int
    stored_message_count: int = 0
    stored_notification_count: int = 0
    events: list[FacebookWebhookEventEntity] = field(default_factory=list)
    message: str = ""


@dataclass(slots=True)
class MessageListResponse:
    platform: str
    items: list[FacebookMessageEntity] = field(default_factory=list)
    total: int = 0
    message: str = ""


@dataclass(slots=True)
class NotificationListResponse:
    platform: str
    items: list[FacebookNotificationEntity] = field(default_factory=list)
    total: int = 0
    message: str = ""
