from __future__ import annotations

from .VN import NewsService as VNNewsService
from .VN import extract_news_filters, is_news_query, looks_like_daily_news_request
from .schemas import NewsQuery, NewsServiceResult
from .world import WorldNewsService, detect_news_scope, looks_like_world_news_request


class NewsService:
    """Coordinate domestic and world news sources."""

    def __init__(
        self,
        *,
        api_key: str,
        world_api_key: str = "",
        default_language: str = "vi",
        default_country: str = "vn",
        default_limit: int = 6,
        timeout_seconds: float = 8.0,
    ) -> None:
        self.default_language = default_language
        self.default_country = default_country
        self.default_limit = default_limit
        self.vn_service = VNNewsService(
            api_key=api_key,
            default_language=default_language,
            default_country=default_country,
            default_limit=default_limit,
            timeout_seconds=timeout_seconds,
        )
        self.world_service = WorldNewsService(
            api_key=world_api_key,
            default_limit=default_limit,
            timeout_seconds=timeout_seconds,
        )

    def parse_query(self, user_text: str) -> NewsQuery:
        base_query = extract_news_filters(
            user_text,
            default_language=self.default_language,
            default_country=self.default_country,
            default_limit=self.default_limit,
        )
        scope = detect_news_scope(
            user_text,
            country_code=base_query.country,
            topic=base_query.topic,
        )
        if scope == "world":
            return self.world_service.parse_query(user_text)
        return self.vn_service.parse_query(user_text)

    def handle_user_query(self, user_text: str) -> NewsServiceResult:
        text = str(user_text or "").strip()
        if not text:
            query = self.parse_query(text)
            return NewsServiceResult(
                is_news_intent=False,
                status="not_news",
                query=query,
                articles=[],
                agent_context="",
                fallback_message="",
                error=None,
            )

        base_query = extract_news_filters(
            text,
            default_language=self.default_language,
            default_country=self.default_country,
            default_limit=self.default_limit,
        )
        scope = detect_news_scope(
            text,
            country_code=base_query.country,
            topic=base_query.topic,
        )
        is_supported_news_intent = is_news_query(text) or (
            scope == "vn" and looks_like_daily_news_request(text)
        ) or (
            scope == "world" and looks_like_world_news_request(text)
        )
        if not is_supported_news_intent:
            query = self.parse_query(text)
            return NewsServiceResult(
                is_news_intent=False,
                status="not_news",
                query=query,
                articles=[],
                agent_context="",
                fallback_message="",
                error=None,
            )

        query = self.parse_query(text)
        scope = detect_news_scope(
            text,
            country_code=query.country,
            topic=query.topic,
        )
        if scope == "world":
            return self.world_service.handle_user_query(text)
        return self.vn_service.handle_user_query(text)


__all__ = ["NewsService", "VNNewsService", "WorldNewsService"]
