"""Immediate user feedback for commands that perform public web searches."""

from __future__ import annotations

from friday.app.browser_automation.intents import is_browser_search_request
from friday.news import (
    is_news_query,
    looks_like_daily_news_request,
    looks_like_world_news_request,
)

from .intents import is_web_research_request


SEARCH_ACKNOWLEDGEMENT = "Give me search Boss, let me check."


def should_announce_search(message: str) -> bool:
    """Return whether FRIDAY will perform a visible or background web search."""
    return any(
        (
            is_browser_search_request(message),
            is_web_research_request(message),
            is_news_query(message),
            looks_like_daily_news_request(message),
            looks_like_world_news_request(message),
        )
    )
