from __future__ import annotations

import re

from .schemas import NewsArticle, NewsQuery


def _normalize_whitespace(text: str) -> str:
    cleaned = str(text or "").replace("\r", " ").replace("\n", " ")
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def _truncate(text: str, *, max_chars: int) -> str:
    content = _normalize_whitespace(text)
    if len(content) <= max_chars:
        return content
    return content[: max_chars - 3].rstrip() + "..."


def clean_article(article: NewsArticle, *, description_max_chars: int = 220) -> NewsArticle | None:
    title = _normalize_whitespace(article.title)
    if not title:
        return None

    description = _truncate(article.description, max_chars=description_max_chars)
    source_name = _normalize_whitespace(article.source_name or article.source_id)
    pub_date = _normalize_whitespace(article.pub_date)
    link = _normalize_whitespace(article.link)
    language = _normalize_whitespace(article.language).lower()

    category = [c for c in (_normalize_whitespace(x).lower() for x in article.category) if c]
    country = [c for c in (_normalize_whitespace(x).lower() for x in article.country) if c]

    return NewsArticle(
        title=title,
        description=description,
        source_id=_normalize_whitespace(article.source_id),
        source_name=source_name,
        pub_date=pub_date,
        link=link,
        category=category,
        country=country,
        language=language,
    )


def normalize_articles(articles: list[NewsArticle], *, limit: int) -> list[NewsArticle]:
    seen_titles: set[str] = set()
    cleaned_articles: list[NewsArticle] = []

    for article in articles:
        cleaned = clean_article(article)
        if cleaned is None:
            continue
        title_key = cleaned.title.lower()
        if title_key in seen_titles:
            continue
        seen_titles.add(title_key)
        cleaned_articles.append(cleaned)
        if len(cleaned_articles) >= limit:
            break

    return cleaned_articles


def article_to_digest_line(article: NewsArticle, *, index: int) -> str:
    source = article.source_name or article.source_id or "unknown"
    lead = article.description or "No description available."
    return f"{index}. {article.title} | Nguon: {source} | Tom tat: {lead}"


def build_articles_digest(articles: list[NewsArticle]) -> str:
    if not articles:
        return "No relevant articles are available."
    lines = [article_to_digest_line(article, index=i + 1) for i, article in enumerate(articles)]
    return "\n".join(lines)


def build_agent_news_context(
    *,
    query: NewsQuery,
    articles: list[NewsArticle],
    status: str,
    fallback_message: str = "",
) -> str:
    topic = query.topic or "general"
    country = query.country or "none"
    language = query.language or "vi"
    digest = build_articles_digest(articles)

    if status != "ok":
        safe_fallback = fallback_message or "No relevant news feed is available right now."
        return (
            "[NEWS_CONTEXT]\n"
            f"status={status}\n"
            f"topic={topic}\n"
            f"country={country}\n"
            f"language={language}\n"
            "article_count=0\n"
            f"fallback_user_message={safe_fallback}\n"
            "response_rules=When status is not ok, reply briefly in English using fallback_user_message and hide implementation details."
        )

    return (
        "[NEWS_CONTEXT]\n"
        "status=ok\n"
        f"topic={topic}\n"
        f"country={country}\n"
        f"language={language}\n"
        f"article_count={len(articles)}\n"
        "response_rules=Summarize in three to five concise English sentences in FRIDAY's voice; never return raw JSON or tool names.\n"
        "articles_digest=\n"
        f"{digest}"
    )


def build_news_fallback_message(*, reason: str) -> str:
    if reason == "missing_api_key":
        return "The news feed is not fully configured, boss. Should I retry after the key is updated?"
    if reason in {"network_error", "timeout", "io_error"}:
        return "The news feed is unstable, boss. I will retry when the connection improves."
    if reason == "no_data":
        return "No news currently matches this request, boss."
    return "I could not retrieve a relevant news feed, boss."
