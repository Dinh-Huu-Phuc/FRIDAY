"""Response mapper for YouTube."""

from __future__ import annotations

from friday.app.youtube.schemas.entities import YouTubeChannelEntity, YouTubeVideoEntity
from friday.app.youtube.schemas.responses import (
    ContentDetailResponse,
    ContentSearchResponse,
    OpenPlatformResponse,
    ProfileResponse,
    PublishContentResponse,
)


class YouTubeMapper:
    """Map YouTube domain entities into outward-facing responses."""

    def __init__(self, *, platform_name: str) -> None:
        self.platform_name = platform_name

    def to_open_response(self, *, url: str, message: str, opened: bool) -> OpenPlatformResponse:
        return OpenPlatformResponse(
            platform=self.platform_name,
            url=url,
            message=message,
            opened=opened,
        )

    def to_profile_response(self, entity: YouTubeChannelEntity) -> ProfileResponse:
        return ProfileResponse(platform=self.platform_name, profile=entity)

    def to_search_response(
        self,
        *,
        query: str,
        items: list[YouTubeVideoEntity],
    ) -> ContentSearchResponse:
        return ContentSearchResponse(
            platform=self.platform_name,
            query=query,
            items=items,
        )

    def to_detail_response(self, entity: YouTubeVideoEntity) -> ContentDetailResponse:
        return ContentDetailResponse(platform=self.platform_name, item=entity)

    def to_publish_response(self, entity: YouTubeVideoEntity) -> PublishContentResponse:
        return PublishContentResponse(platform=self.platform_name, item=entity)
