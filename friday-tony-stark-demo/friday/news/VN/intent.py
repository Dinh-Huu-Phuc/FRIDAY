from __future__ import annotations

import re

from .constants import (
    COUNTRY_ALIAS_TO_CODE, DEFAULT_NEWS_COUNTRY, DEFAULT_NEWS_LANGUAGE,
    DEFAULT_NEWS_LIMIT, LANGUAGE_ALIAS_TO_CODE, MAX_NEWS_LIMIT,
    NEWS_INTENT_KEYWORDS, TOPIC_ALIAS_TO_API_CATEGORY,
)
from .schemas import NewsQuery


def _normalize_for_match(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "").lower().strip())


def is_news_query(text: str) -> bool:
    normalized = _normalize_for_match(text)
    if not normalized:
        return False
    if any(keyword in normalized for keyword in NEWS_INTENT_KEYWORDS):
        return True
    if any(
        phrase in normalized
        for phrase in (
            "what's new",
            "whats new",
            "what is new",
            "daily briefing",
            "start my day",
            "today's summary",
            "todays summary",
        )
    ):
        return True
    has_topic = any(alias in normalized for alias in TOPIC_ALIAS_TO_API_CATEGORY)
    has_news_word = any(word in normalized for word in ("news", "headline", "briefing"))
    has_update_phrase = any(
        phrase in normalized
        for phrase in ("what is new", "today", "notable", "update", "summary", "latest")
    )
    return has_topic and (has_news_word or has_update_phrase)


def looks_like_daily_news_request(text: str) -> bool:
    normalized = _normalize_for_match(text)
    has_news_word = any(word in normalized for word in ("news", "headline", "briefing"))
    has_update_phrase = any(
        phrase in normalized
        for phrase in ("what is new", "today", "notable", "update", "summary", "latest", "domestic", "vietnam")
    )
    return bool(normalized and has_news_word and has_update_phrase)


def _detect_topic(normalized_text: str) -> str | None:
    return next((topic for alias, topic in TOPIC_ALIAS_TO_API_CATEGORY.items() if alias in normalized_text), None)


def _detect_country(normalized_text: str) -> str | None:
    return next((code for alias, code in COUNTRY_ALIAS_TO_CODE.items() if alias in normalized_text), None)


def _detect_language(normalized_text: str, default_language: str) -> str:
    return next((code for alias, code in LANGUAGE_ALIAS_TO_CODE.items() if alias in normalized_text), default_language)


def _detect_limit(normalized_text: str, default_limit: int) -> int:
    match = re.search(r"\b(\d{1,2})\s*(news|articles|items|stories)\b", normalized_text)
    return min(max(int(match.group(1)), 1), MAX_NEWS_LIMIT) if match else default_limit


def extract_news_filters(
    text: str,
    *,
    default_language: str = DEFAULT_NEWS_LANGUAGE,
    default_country: str = DEFAULT_NEWS_COUNTRY,
    default_limit: int = DEFAULT_NEWS_LIMIT,
) -> NewsQuery:
    normalized = _normalize_for_match(text)
    return NewsQuery(
        topic=_detect_topic(normalized),
        country=_detect_country(normalized) or default_country,
        language=_detect_language(normalized, default_language),
        limit=_detect_limit(normalized, default_limit),
        page=None,
        text_query=None,
    )
