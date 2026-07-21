"""Schema exports for the Pinterest package."""

from friday.app.pinterest.schemas.entities import (
    PinterestProfileEntity,
    PinterestPinEntity,
    PinterestBoardEntity,
    PinterestCommentEntity,
)
from friday.app.pinterest.schemas.requests import (
    GetPostDetailRequest,
    GetProfileRequest,
    OpenPlatformRequest,
    PublishContentRequest,
    SearchContentRequest,
)
from friday.app.pinterest.schemas.responses import (
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
