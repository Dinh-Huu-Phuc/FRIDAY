from __future__ import annotations

from ...VN.formatter import build_articles_digest, normalize_articles
from ...schemas import NewsArticle, NewsQuery


def build_world_agent_news_context(
    *,
    query: NewsQuery,
    articles: list[NewsArticle],
    status: str,
    fallback_message: str = "",
) -> str:
    topic = query.topic or "world"
    digest = build_articles_digest(articles)

    if status != "ok":
        safe_fallback = fallback_message or "No relevant world news feed is available right now."
        return (
            "[NEWS_CONTEXT]\n"
            f"status={status}\n"
            "scope=world\n"
            f"topic={topic}\n"
            f"search_query={query.text_query or ''}\n"
            "article_count=0\n"
            f"fallback_user_message={safe_fallback}\n"
            "response_rules=Reply briefly in English, identify this as world news, and hide implementation details."
        )

    return (
        "[NEWS_CONTEXT]\n"
        "status=ok\n"
        "scope=world\n"
        f"topic={topic}\n"
        f"search_query={query.text_query or ''}\n"
        f"article_count={len(articles)}\n"
        "response_rules=Summarize in three to five concise English sentences, identify this as world news, and never return raw JSON.\n"
        "articles_digest=\n"
        f"{digest}"
    )


def build_world_news_fallback_message(*, reason: str) -> str:
    if reason == "missing_world_api_key":
        return "The world news feed is not fully configured, boss. Should I retry after WORLD_NEWS is updated?"
    if reason in {"network_error", "timeout", "io_error"}:
        return "The world news connection is unstable, boss. I will retry when it improves."
    if reason == "no_data":
        return "No world news articles currently match this request, boss."
    return "I could not retrieve a relevant world news feed, boss."
