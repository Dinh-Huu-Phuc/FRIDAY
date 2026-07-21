"""Response models for the LinkedIn package."""

from __future__ import annotations

from dataclasses import dataclass, field

from friday.app.linkedin.schemas.entities import LinkedInProfileEntity, LinkedInPostEntity


@dataclass(slots=True)
class OpenPlatformResponse:
    platform: str
    url: str
    message: str
    opened: bool


@dataclass(slots=True)
class ProfileResponse:
    platform: str
    profile: LinkedInProfileEntity


@dataclass(slots=True)
class ContentSearchResponse:
    platform: str
    query: str
    items: list[LinkedInPostEntity] = field(default_factory=list)


@dataclass(slots=True)
class ContentDetailResponse:
    platform: str
    item: LinkedInPostEntity


@dataclass(slots=True)
class PublishContentResponse:
    platform: str
    item: LinkedInPostEntity
    status: str = "queued"
