"""Request models for the X package."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class OpenPlatformRequest:
    command: str = ""
    platform: str = "x"
    open_in_new_tab: bool = True


@dataclass(slots=True)
class GetProfileRequest:
    identifier: str = ""
    username: str = ""
    include_related: bool = False


@dataclass(slots=True)
class SearchContentRequest:
    query: str
    limit: int = 10
    filters: dict[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class GetPostDetailRequest:
    content_id: str
    expand_comments: bool = False


@dataclass(slots=True)
class PublishContentRequest:
    title: str
    body: str
    visibility: str = "private"
    attachments: list[str] = field(default_factory=list)
