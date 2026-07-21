from __future__ import annotations

import logging

from ...intent import extract_news_filters, is_news_query
from ...schemas import NewsQuery, NewsServiceResult
from ..region import build_world_query_text, looks_like_world_news_request, resolve_world_topic
from .client import DEFAULT_WORLD_NEWS_TIMEOUT, WorldNewsAPIClient
from .formatter import (
    build_world_agent_news_context,
    build_world_news_fallback_message,
    normalize_articles,
)

logger = logging.getLogger("friday-world-news-service")


class WorldNewsService:
    """World news service backed by NewsAPI."""

    def __init__(
        self,
        *,
        api_key: str,
        default_language: str = "en",
        default_country: str = "world",
        default_limit: int = 6,
        timeout_seconds: float = DEFAULT_WORLD_NEWS_TIMEOUT,
    ) -> None:
        self.default_language = default_language
        self.default_country = default_country
        self.default_limit = default_limit
        self.client = WorldNewsAPIClient(
            api_key=api_key,
            timeout_seconds=timeout_seconds,
        )

    def parse_query(self, user_text: str) -> NewsQuery:
        base_query = extract_news_filters(
            user_text,
            default_language="en",
            default_country="world",
            default_limit=self.default_limit,
        )
        resolved_topic = resolve_world_topic(
            user_text,
            fallback_topic=base_query.topic or "world",
        )
        return NewsQuery(
            topic=resolved_topic,
            country="world",
            language="en",
            limit=base_query.limit,
            page=None,
            text_query=build_world_query_text(
                user_text=user_text,
                topic=resolved_topic,
            ),
        )

    def handle_user_query(self, user_text: str) -> NewsServiceResult:
        text = str(user_text or "").strip()
        if not text:
            query = self.parse_query("")
            return NewsServiceResult(
                is_news_intent=False,
                status="not_news",
                query=query,
                articles=[],
                agent_context="",
                fallback_message="",
                error=None,
            )

        if not (is_news_query(text) or looks_like_world_news_request(text)):
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
        fetch_result = self.client.fetch_latest(query)

        if not fetch_result.ok:
            reason = str(fetch_result.error or "api_error").split(":", maxsplit=1)[0]
            fallback = build_world_news_fallback_message(reason=reason)
            context = build_world_agent_news_context(
                query=query,
                articles=[],
                status="error",
                fallback_message=fallback,
            )
            return NewsServiceResult(
                is_news_intent=True,
                status="error",
                query=query,
                articles=[],
                agent_context=context,
                fallback_message=fallback,
                error=fetch_result.error,
            )

        cleaned = normalize_articles(fetch_result.articles, limit=query.limit)
        if not cleaned:
            fallback = build_world_news_fallback_message(reason="no_data")
            context = build_world_agent_news_context(
                query=query,
                articles=[],
                status="no_data",
                fallback_message=fallback,
            )
            return NewsServiceResult(
                is_news_intent=True,
                status="no_data",
                query=query,
                articles=[],
                agent_context=context,
                fallback_message=fallback,
                error=None,
            )

        context = build_world_agent_news_context(
            query=query,
            articles=cleaned,
            status="ok",
            fallback_message="",
        )

        logger.info(
            "World news fetched status=ok topic=%s query=%s count=%s",
            query.topic,
            query.text_query,
            len(cleaned),
        )

        return NewsServiceResult(
            is_news_intent=True,
            status="ok",
            query=query,
            articles=cleaned,
            agent_context=context,
            fallback_message="",
            error=None,
        )
