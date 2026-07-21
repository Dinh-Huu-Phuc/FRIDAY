from __future__ import annotations

import logging

from .client import NewsDataClient
from .constants import (
    DEFAULT_NEWS_COUNTRY,
    DEFAULT_NEWS_LANGUAGE,
    DEFAULT_NEWS_LIMIT,
    DEFAULT_NEWS_REQUEST_TIMEOUT,
)
from .formatter import (
    build_agent_news_context,
    build_news_fallback_message,
    normalize_articles,
)
from .intent import extract_news_filters, is_news_query, looks_like_daily_news_request
from .schemas import NewsQuery, NewsServiceResult

logger = logging.getLogger("friday-news-service")


class NewsService:
    """
    News orchestration layer used by the agent runtime.
    """

    def __init__(
        self,
        *,
        api_key: str,
        default_language: str = DEFAULT_NEWS_LANGUAGE,
        default_country: str = DEFAULT_NEWS_COUNTRY,
        default_limit: int = DEFAULT_NEWS_LIMIT,
        timeout_seconds: float = DEFAULT_NEWS_REQUEST_TIMEOUT,
    ) -> None:
        self.default_language = default_language
        self.default_country = default_country
        self.default_limit = default_limit
        self.client = NewsDataClient(
            api_key=api_key,
            timeout_seconds=timeout_seconds,
        )

    def parse_query(self, user_text: str) -> NewsQuery:
        return extract_news_filters(
            user_text,
            default_language=self.default_language,
            default_country=self.default_country,
            default_limit=self.default_limit,
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

        if not (is_news_query(text) or looks_like_daily_news_request(text)):
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
            fallback = build_news_fallback_message(reason=reason)
            context = build_agent_news_context(
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
            fallback = build_news_fallback_message(reason="no_data")
            context = build_agent_news_context(
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

        context = build_agent_news_context(
            query=query,
            articles=cleaned,
            status="ok",
            fallback_message="",
        )

        logger.info(
            "News fetched status=ok topic=%s country=%s language=%s count=%s",
            query.topic,
            query.country,
            query.language,
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
