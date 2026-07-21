"""Schema exports for the Instagram package."""

from friday.app.instagram.schemas.entities import (
    InstagramProfileEntity,
    InstagramPostEntity,
    InstagramReelEntity,
    InstagramStoryEntity,
    InstagramCommentEntity,
)
from friday.app.instagram.schemas.requests import (
    GetPostDetailRequest,
    GetProfileRequest,
    OpenPlatformRequest,
    PublishContentRequest,
    SearchContentRequest,
)
from friday.app.instagram.schemas.responses import (
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
