"""Response models for the X package."""

from __future__ import annotations

from dataclasses import dataclass, field

from friday.app.x.schemas.entities import XAccountEntity, XTweetEntity


@dataclass(slots=True)
class OpenPlatformResponse:
    platform: str
    url: str
    message: str
    opened: bool


@dataclass(slots=True)
class ProfileResponse:
    platform: str
    profile: XAccountEntity


@dataclass(slots=True)
class ContentSearchResponse:
    platform: str
    query: str
    items: list[XTweetEntity] = field(default_factory=list)


@dataclass(slots=True)
class ContentDetailResponse:
    platform: str
    item: XTweetEntity


@dataclass(slots=True)
class PublishContentResponse:
    platform: str
    item: XTweetEntity
    status: str = "queued"
