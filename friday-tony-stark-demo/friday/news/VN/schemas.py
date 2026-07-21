from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class NewsArticle:
    title: str
    description: str
    source_id: str
    source_name: str
    pub_date: str
    link: str
    category: list[str] = field(default_factory=list)
    country: list[str] = field(default_factory=list)
    language: str = ""

    @classmethod
    def from_api_item(cls, item: dict[str, Any]) -> "NewsArticle":
        category_raw = item.get("category")
        country_raw = item.get("country")

        if isinstance(category_raw, list):
            category = [str(v).strip() for v in category_raw if str(v).strip()]
        elif category_raw:
            category = [str(category_raw).strip()]
        else:
            category = []

        if isinstance(country_raw, list):
            country = [str(v).strip().lower() for v in country_raw if str(v).strip()]
        elif country_raw:
            country = [str(country_raw).strip().lower()]
        else:
            country = []

        source_id = str(item.get("source_id") or "").strip()
        source_name = str(item.get("source_name") or source_id).strip()
        language = str(item.get("language") or "").strip().lower()

        return cls(
            title=str(item.get("title") or "").strip(),
            description=str(item.get("description") or "").strip(),
            source_id=source_id,
            source_name=source_name,
            pub_date=str(item.get("pubDate") or item.get("pub_date") or "").strip(),
            link=str(item.get("link") or "").strip(),
            category=category,
            country=country,
            language=language,
        )


@dataclass(slots=True)
class NewsQuery:
    topic: str | None = None
    country: str | None = None
    language: str = "vi"
    limit: int = 6
    page: str | None = None
    text_query: str | None = None


@dataclass(slots=True)
class NewsFetchResult:
    ok: bool
    query: NewsQuery
    articles: list[NewsArticle] = field(default_factory=list)
    error: str | None = None
    status_code: int | None = None
    total_results: int = 0
    raw_status: str = ""
    next_page: str | None = None


@dataclass(slots=True)
class NewsServiceResult:
    is_news_intent: bool
    status: str
    query: NewsQuery
    articles: list[NewsArticle] = field(default_factory=list)
    agent_context: str = ""
    fallback_message: str = ""
    error: str | None = None

    @property
    def article_count(self) -> int:
        return len(self.articles)
