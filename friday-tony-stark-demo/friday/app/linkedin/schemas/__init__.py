"""Schema exports for the LinkedIn package."""

from friday.app.linkedin.schemas.entities import (
    LinkedInProfileEntity,
    LinkedInPostEntity,
    LinkedInCompanyPageEntity,
    LinkedInCommentEntity,
)
from friday.app.linkedin.schemas.requests import (
    GetPostDetailRequest,
    GetProfileRequest,
    OpenPlatformRequest,
    PublishContentRequest,
    SearchContentRequest,
)
from friday.app.linkedin.schemas.responses import (
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
