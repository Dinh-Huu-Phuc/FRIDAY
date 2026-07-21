"""Response models for the Discord package."""

from __future__ import annotations

from dataclasses import dataclass, field

from friday.app.discord.schemas.entities import DiscordGuildEntity, DiscordMessageEntity


@dataclass(slots=True)
class OpenPlatformResponse:
    platform: str
    url: str
    message: str
    opened: bool


@dataclass(slots=True)
class ProfileResponse:
    platform: str
    profile: DiscordGuildEntity


@dataclass(slots=True)
class ContentSearchResponse:
    platform: str
    query: str
    items: list[DiscordMessageEntity] = field(default_factory=list)


@dataclass(slots=True)
class ContentDetailResponse:
    platform: str
    item: DiscordMessageEntity


@dataclass(slots=True)
class PublishContentResponse:
    platform: str
    item: DiscordMessageEntity
    status: str = "queued"
