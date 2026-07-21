from __future__ import annotations

import json
import logging
from datetime import UTC, datetime, timedelta
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from ...schemas import NewsArticle, NewsFetchResult, NewsQuery

logger = logging.getLogger("friday-world-news-client")

WORLD_NEWS_ENDPOINT = "https://newsapi.org/v2/everything"
DEFAULT_WORLD_NEWS_TIMEOUT = 8.0


class WorldNewsAPIClient:
    """HTTP client for world news via NewsAPI Everything endpoint."""

    def __init__(
        self,
        *,
        api_key: str,
        endpoint: str = WORLD_NEWS_ENDPOINT,
        timeout_seconds: float = DEFAULT_WORLD_NEWS_TIMEOUT,
    ) -> None:
        self.api_key = api_key.strip()
        self.endpoint = endpoint
        self.timeout_seconds = timeout_seconds

    def fetch_latest(self, query: NewsQuery) -> NewsFetchResult:
        if not self.api_key:
            return NewsFetchResult(
                ok=False,
                query=query,
                error="missing_world_api_key",
                status_code=None,
            )

        now = datetime.now(UTC)
        from_date = (now - timedelta(days=1)).strftime("%Y-%m-%d")
        to_date = now.strftime("%Y-%m-%d")

        params: dict[str, str] = {
            "q": query.text_query or "world",
            "from": from_date,
            "to": to_date,
            "sortBy": "publishedAt",
            "language": "en",
            "pageSize": str(max(1, min(query.limit, 20))),
            "apiKey": self.api_key,
        }

        request_url = f"{self.endpoint}?{urlencode(params)}"
        request = Request(request_url, method="GET")

        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                status_code = getattr(response, "status", None)
                body_text = response.read().decode("utf-8")
        except HTTPError as exc:
            logger.warning("World News API HTTP error status=%s", exc.code)
            return NewsFetchResult(
                ok=False,
                query=query,
                error=f"http_error:{exc.code}",
                status_code=exc.code,
            )
        except URLError as exc:
            logger.warning("World News API network error reason=%s", exc.reason)
            return NewsFetchResult(
                ok=False,
                query=query,
                error="network_error",
                status_code=None,
            )
        except TimeoutError:
            logger.warning("World News API timeout")
            return NewsFetchResult(
                ok=False,
                query=query,
                error="timeout",
                status_code=None,
            )
        except OSError:
            logger.warning("World News API OS error while requesting endpoint")
            return NewsFetchResult(
                ok=False,
                query=query,
                error="io_error",
                status_code=None,
            )

        if status_code and status_code >= 400:
            return NewsFetchResult(
                ok=False,
                query=query,
                error=f"http_error:{status_code}",
                status_code=status_code,
            )

        try:
            payload = json.loads(body_text)
        except json.JSONDecodeError:
            logger.warning("World News API invalid JSON payload")
            return NewsFetchResult(
                ok=False,
                query=query,
                error="invalid_json",
                status_code=status_code,
            )

        if not isinstance(payload, dict):
            return NewsFetchResult(
                ok=False,
                query=query,
                error="invalid_payload",
                status_code=status_code,
            )

        raw_status = str(payload.get("status") or "").lower()
        if raw_status != "ok":
            error_message = str(payload.get("message") or "api_error").strip()
            logger.warning("World News API returned error payload=%s", error_message[:200])
            return NewsFetchResult(
                ok=False,
                query=query,
                error=f"api_error:{error_message}",
                status_code=status_code,
                raw_status=raw_status,
            )

        results = payload.get("articles")
        if not isinstance(results, list):
            return NewsFetchResult(
                ok=False,
                query=query,
                error="invalid_results",
                status_code=status_code,
                raw_status=raw_status,
            )

        articles: list[NewsArticle] = []
        for item in results:
            if not isinstance(item, dict):
                continue
            source_payload = item.get("source") or {}
            source_id = str(source_payload.get("id") or "").strip()
            source_name = str(source_payload.get("name") or source_id or "Unknown").strip()
            articles.append(
                NewsArticle(
                    title=str(item.get("title") or "").strip(),
                    description=str(item.get("description") or "").strip(),
                    source_id=source_id,
                    source_name=source_name,
                    pub_date=str(item.get("publishedAt") or "").strip(),
                    link=str(item.get("url") or "").strip(),
                    category=[query.topic] if query.topic else ["world"],
                    country=["world"],
                    language="en",
                )
            )

        return NewsFetchResult(
            ok=True,
            query=query,
            articles=articles,
            error=None,
            status_code=status_code,
            total_results=len(articles),
            raw_status=raw_status,
            next_page=None,
        )
