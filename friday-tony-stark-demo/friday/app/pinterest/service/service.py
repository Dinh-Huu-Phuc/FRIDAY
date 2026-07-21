"""High-level orchestration service for Pinterest."""

from __future__ import annotations

from friday.app.pinterest.config.settings import PinterestSettings
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
from friday.app.pinterest.service.client import PinterestClient
from friday.app.pinterest.service.mapper import PinterestMapper
from friday.app.pinterest.service.parser import PinterestParser


class PinterestService:
    """Coordinate client, parser, and mapper calls for Pinterest."""

    def __init__(
        self,
        *,
        settings: PinterestSettings,
        client: PinterestClient,
        parser: PinterestParser,
        mapper: PinterestMapper,
    ) -> None:
        self.settings = settings
        self.client = client
        self.parser = parser
        self.mapper = mapper

    def open_platform_homepage(
        self,
        request: OpenPlatformRequest | None = None,
    ) -> OpenPlatformResponse:
        _ = request
        result = self.client.open_homepage()
        return self.mapper.to_open_response(
            url=result.url,
            message=result.message,
            opened=result.opened_in_new_tab,
        )

    def get_profile(self, request: GetProfileRequest) -> ProfileResponse:
        payload = self.client.get_profile(request)
        entity = self.parser.parse_profile(payload)
        return self.mapper.to_profile_response(entity)

    def search_content(self, request: SearchContentRequest) -> ContentSearchResponse:
        payloads = self.client.search_content(request)
        items = [self.parser.parse_pin(payload) for payload in payloads]
        return self.mapper.to_search_response(query=request.query, items=items)

    def get_post_detail(self, request: GetPostDetailRequest) -> ContentDetailResponse:
        payload = self.client.get_post_detail(request)
        entity = self.parser.parse_pin(payload)
        return self.mapper.to_detail_response(entity)

    def publish_content(self, request: PublishContentRequest) -> PublishContentResponse:
        payload = self.client.publish_content(request)
        entity = self.parser.parse_pin(payload)
        return self.mapper.to_publish_response(entity)
