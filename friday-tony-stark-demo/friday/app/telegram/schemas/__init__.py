"""Schema exports for the Telegram package."""

from friday.app.telegram.schemas.entities import (
    TelegramChatEntity,
    TelegramMessageEntity,
    TelegramChannelEntity,
)
from friday.app.telegram.schemas.requests import (
    GetPostDetailRequest,
    GetProfileRequest,
    OpenPlatformRequest,
    PublishContentRequest,
    SearchContentRequest,
)
from friday.app.telegram.schemas.responses import (
    ContentDetailResponse,
    ContentSearchResponse,
    OpenPlatformResponse,
    ProfileResponse,
    PublishContentResponse,
)

__all__ = [
    "ContentDetailResponse",
    "ContentSearchResponse",
    "GetPostDetailRequest",
    "GetProfileRequest",
    "OpenPlatformRequest",
    "OpenPlatformResponse",
    "ProfileResponse",
    "PublishContentRequest",
    "PublishContentResponse",
    "SearchContentRequest",
]
