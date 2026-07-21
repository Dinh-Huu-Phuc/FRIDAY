from __future__ import annotations

import json
import logging
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .constants import (
    DEFAULT_NEWS_REQUEST_TIMEOUT,
    NEWS_API_ENDPOINT,
)
from .schemas import NewsArticle, NewsFetchResult, NewsQuery

logger = logging.getLogger("friday-news-client")


class NewsDataClient:
    """
    Thin HTTP client for NewsData latest endpoint.
    """

    def __init__(
        self,
        *,
        api_key: str,
        endpoint: str = NEWS_API_ENDPOINT,
        timeout_seconds: float = DEFAULT_NEWS_REQUEST_TIMEOUT,
    ) -> None:
        self.api_key = api_key.strip()
        self.endpoint = endpoint
        self.timeout_seconds = timeout_seconds

    def fetch_latest(self, query: NewsQuery) -> NewsFetchResult:
        if not self.api_key:
            return NewsFetchResult(
                ok=False,
                query=query,
                error="missing_api_key",
                status_code=None,
            )

        params: dict[str, str] = {
            "apikey": self.api_key,
            "language": query.language,
        }
        if query.country:
            params["country"] = query.country
        if query.topic:
            params["category"] = query.topic
        if query.page:
            params["page"] = query.page
        if query.limit > 0:
            params["size"] = str(query.limit)
        if query.text_query:
            params["q"] = query.text_query

        request_url = f"{self.endpoint}?{urlencode(params)}"
        request = Request(request_url, method="GET")

        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                status_code = getattr(response, "status", None)
                body_text = response.read().decode("utf-8")
        except HTTPError as exc:
            logger.warning("NewsData HTTP error status=%s", exc.code)
            return NewsFetchResult(
                ok=False,
                query=query,
                error=f"http_error:{exc.code}",
                status_code=exc.code,
            )
        except URLError as exc:
            logger.warning("NewsData network error reason=%s", exc.reason)
            return NewsFetchResult(
                ok=False,
                query=query,
                error="network_error",
                status_code=None,
            )
        except TimeoutError:
            logger.warning("NewsData timeout")
            return NewsFetchResult(
                ok=False,
                query=query,
                error="timeout",
                status_code=None,
            )
        except OSError:
            logger.warning("NewsData OS error while requesting endpoint")
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
            logger.warning("NewsData invalid JSON payload")
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
        if raw_status == "error":
            error_message = str(payload.get("results") or payload.get("message") or "api_error").strip()
            logger.warning("NewsData returned error payload=%s", error_message[:200])
            return NewsFetchResult(
                ok=False,
                query=query,
                error=f"api_error:{error_message}",
                status_code=status_code,
                raw_status=raw_status,
            )

        results = payload.get("results")
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
            if isinstance(item, dict):
                article = NewsArticle.from_api_item(item)
                articles.append(article)

        return NewsFetchResult(
            ok=True,
            query=query,
            articles=articles,
            error=None,
            status_code=status_code,
            total_results=len(articles),
            raw_status=raw_status,
            next_page=str(payload.get("nextPage") or "").strip() or None,
        )
