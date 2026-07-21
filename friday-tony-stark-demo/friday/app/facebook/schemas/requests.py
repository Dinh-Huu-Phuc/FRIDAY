"""Request models for the Facebook package."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class OpenPlatformRequest:
    command: str = ""
    platform: str = "facebook"
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


@dataclass(slots=True)
class VerifyWebhookRequest:
    mode: str
    verify_token: str
    challenge: str = ""
    object_type: str = "page"


@dataclass(slots=True)
class ReceiveWebhookRequest:
    payload: dict[str, object]
    signature: str | None = None
    raw_body: str = ""


@dataclass(slots=True)
class CheckMessagesRequest:
    limit: int = 10
    unread_only: bool = False
    sender_id: str = ""


@dataclass(slots=True)
class CheckNotificationsRequest:
    limit: int = 10
    event_types: list[str] = field(default_factory=list)
