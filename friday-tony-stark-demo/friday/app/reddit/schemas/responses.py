"""Response models for the Reddit package."""

from __future__ import annotations

from dataclasses import dataclass, field

from friday.app.reddit.schemas.entities import RedditSubredditEntity, RedditPostEntity


@dataclass(slots=True)
class OpenPlatformResponse:
    platform: str
    url: str
    message: str
    opened: bool


@dataclass(slots=True)
class ProfileResponse:
    platform: str
    profile: RedditSubredditEntity


@dataclass(slots=True)
class ContentSearchResponse:
    platform: str
    query: str
    items: list[RedditPostEntity] = field(default_factory=list)


@dataclass(slots=True)
class ContentDetailResponse:
    platform: str
    item: RedditPostEntity


@dataclass(slots=True)
class PublishContentResponse:
    platform: str
    item: RedditPostEntity
    status: str = "queued"
