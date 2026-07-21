"""Response models for the Instagram package."""

from __future__ import annotations

from dataclasses import dataclass, field

from friday.app.instagram.schemas.entities import InstagramProfileEntity, InstagramPostEntity


@dataclass(slots=True)
class OpenPlatformResponse:
    platform: str
    url: str
    message: str
    opened: bool


@dataclass(slots=True)
class ProfileResponse:
    platform: str
    profile: InstagramProfileEntity


@dataclass(slots=True)
class ContentSearchResponse:
    platform: str
    query: str
    items: list[InstagramPostEntity] = field(default_factory=list)


@dataclass(slots=True)
class ContentDetailResponse:
    platform: str
    item: InstagramPostEntity


@dataclass(slots=True)
class PublishContentResponse:
    platform: str
    item: InstagramPostEntity
    status: str = "queued"
