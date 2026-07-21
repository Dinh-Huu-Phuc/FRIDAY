"""Response mapper for Discord."""

from __future__ import annotations

from friday.app.discord.schemas.entities import DiscordGuildEntity, DiscordMessageEntity
from friday.app.discord.schemas.responses import (
    ContentDetailResponse,
    ContentSearchResponse,
    OpenPlatformResponse,
    ProfileResponse,
    PublishContentResponse,
)


class DiscordMapper:
    """Map Discord domain entities into outward-facing responses."""

    def __init__(self, *, platform_name: str) -> None:
        self.platform_name = platform_name

    def to_open_response(self, *, url: str, message: str, opened: bool) -> OpenPlatformResponse:
        return OpenPlatformResponse(
            platform=self.platform_name,
            url=url,
            message=message,
            opened=opened,
        )

    def to_profile_response(self, entity: DiscordGuildEntity) -> ProfileResponse:
        return ProfileResponse(platform=self.platform_name, profile=entity)

    def to_search_response(
        self,
        *,
        query: str,
        items: list[DiscordMessageEntity],
    ) -> ContentSearchResponse:
        return ContentSearchResponse(
            platform=self.platform_name,
            query=query,
            items=items,
        )

    def to_detail_response(self, entity: DiscordMessageEntity) -> ContentDetailResponse:
        return ContentDetailResponse(platform=self.platform_name, item=entity)

    def to_publish_response(self, entity: DiscordMessageEntity) -> PublishContentResponse:
        return PublishContentResponse(platform=self.platform_name, item=entity)
