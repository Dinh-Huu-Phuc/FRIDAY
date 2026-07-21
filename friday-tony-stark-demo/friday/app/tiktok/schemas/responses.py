"""Response models for the TikTok package."""

from __future__ import annotations

from dataclasses import dataclass, field

from friday.app.tiktok.schemas.entities import TikTokProfileEntity, TikTokVideoEntity


@dataclass(slots=True)
class OpenPlatformResponse:
    platform: str
    url: str
    message: str
    opened: bool


@dataclass(slots=True)
class ProfileResponse:
    platform: str
    profile: TikTokProfileEntity


@dataclass(slots=True)
class ContentSearchResponse:
    platform: str
    query: str
    items: list[TikTokVideoEntity] = field(default_factory=list)


@dataclass(slots=True)
class ContentDetailResponse:
    platform: str
    item: TikTokVideoEntity


@dataclass(slots=True)
class PublishContentResponse:
    platform: str
    item: TikTokVideoEntity
    status: str = "queued"
