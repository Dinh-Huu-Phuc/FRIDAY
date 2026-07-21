"""Schema exports for the YouTube package."""

from friday.app.youtube.schemas.entities import (
    YouTubeChannelEntity,
    YouTubeVideoEntity,
    YouTubePlaylistEntity,
    YouTubeCommentEntity,
)
from friday.app.youtube.schemas.requests import (
    GetPostDetailRequest,
    GetProfileRequest,
    OpenPlatformRequest,
    PublishContentRequest,
    SearchContentRequest,
)
from friday.app.youtube.schemas.responses import (
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
