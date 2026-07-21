"""Response mapper for X."""

from __future__ import annotations

from friday.app.x.schemas.entities import XAccountEntity, XTweetEntity
from friday.app.x.schemas.responses import (
    ContentDetailResponse,
    ContentSearchResponse,
    OpenPlatformResponse,
    ProfileResponse,
    PublishContentResponse,
)


class XMapper:
    """Map X domain entities into outward-facing responses."""

    def __init__(self, *, platform_name: str) -> None:
        self.platform_name = platform_name

    def to_open_response(self, *, url: str, message: str, opened: bool) -> OpenPlatformResponse:
        return OpenPlatformResponse(
            platform=self.platform_name,
            url=url,
            message=message,
            opened=opened,
        )

    def to_profile_response(self, entity: XAccountEntity) -> ProfileResponse:
        return ProfileResponse(platform=self.platform_name, profile=entity)

    def to_search_response(
        self,
        *,
        query: str,
        items: list[XTweetEntity],
    ) -> ContentSearchResponse:
        return ContentSearchResponse(
            platform=self.platform_name,
            query=query,
            items=items,
        )

    def to_detail_response(self, entity: XTweetEntity) -> ContentDetailResponse:
        return ContentDetailResponse(platform=self.platform_name, item=entity)

    def to_publish_response(self, entity: XTweetEntity) -> PublishContentResponse:
        return PublishContentResponse(platform=self.platform_name, item=entity)
