"""Response models for the YouTube package."""

from __future__ import annotations

from dataclasses import dataclass, field

from friday.app.youtube.schemas.entities import YouTubeChannelEntity, YouTubeVideoEntity


@dataclass(slots=True)
class OpenPlatformResponse:
    platform: str
    url: str
    message: str
    opened: bool


@dataclass(slots=True)
class ProfileResponse:
    platform: str
    profile: YouTubeChannelEntity


@dataclass(slots=True)
class ContentSearchResponse:
    platform: str
    query: str
    items: list[YouTubeVideoEntity] = field(default_factory=list)


@dataclass(slots=True)
class ContentDetailResponse:
    platform: str
    item: YouTubeVideoEntity


@dataclass(slots=True)
class PublishContentResponse:
    platform: str
    item: YouTubeVideoEntity
    status: str = "queued"
