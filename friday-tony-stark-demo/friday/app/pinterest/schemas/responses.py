"""Response models for the Pinterest package."""

from __future__ import annotations

from dataclasses import dataclass, field

from friday.app.pinterest.schemas.entities import PinterestProfileEntity, PinterestPinEntity


@dataclass(slots=True)
class OpenPlatformResponse:
    platform: str
    url: str
    message: str
    opened: bool


@dataclass(slots=True)
class ProfileResponse:
    platform: str
    profile: PinterestProfileEntity


@dataclass(slots=True)
class ContentSearchResponse:
    platform: str
    query: str
    items: list[PinterestPinEntity] = field(default_factory=list)


@dataclass(slots=True)
class ContentDetailResponse:
    platform: str
    item: PinterestPinEntity


@dataclass(slots=True)
class PublishContentResponse:
    platform: str
    item: PinterestPinEntity
    status: str = "queued"
