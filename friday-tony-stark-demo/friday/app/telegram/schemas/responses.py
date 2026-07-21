"""Response models for the Telegram package."""

from __future__ import annotations

from dataclasses import dataclass, field

from friday.app.telegram.schemas.entities import TelegramChatEntity, TelegramMessageEntity


@dataclass(slots=True)
class OpenPlatformResponse:
    platform: str
    url: str
    message: str
    opened: bool


@dataclass(slots=True)
class ProfileResponse:
    platform: str
    profile: TelegramChatEntity


@dataclass(slots=True)
class ContentSearchResponse:
    platform: str
    query: str
    items: list[TelegramMessageEntity] = field(default_factory=list)


@dataclass(slots=True)
class ContentDetailResponse:
    platform: str
    item: TelegramMessageEntity


@dataclass(slots=True)
class PublishContentResponse:
    platform: str
    item: TelegramMessageEntity
    status: str = "queued"
