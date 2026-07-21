from __future__ import annotations

import ipaddress
import re
from html.parser import HTMLParser
from typing import Protocol
from urllib.parse import parse_qs, quote_plus, urljoin, urlparse
from xml.etree import ElementTree

import httpx

from friday.app.browser_automation.schemas import WebSearchResult


_BLOCKED_SUFFIXES = (
    ".7z", ".apk", ".bat", ".cmd", ".dmg", ".exe", ".iso", ".msi", ".ps1", ".rar", ".scr", ".zip"
)
_SKIP_TAGS = {"script", "style", "noscript", "nav", "footer", "header", "form", "svg"}
_NON_ARTICLE_HOSTS = {
    "facebook.com",
    "instagram.com",
    "tiktok.com",
    "vimeo.com",
    "x.com",
    "youtube.com",
    "youtu.be",
}
_PREFERRED_HOST_WEIGHTS = {
    "wikipedia.org": 100,
    "britannica.com": 90,
    "marvel.com": 80,
    "imdb.com": 35,
}


class ResearchProvider(Protocol):
    def search_results(self, query: str, *, limit: int = 5) -> list[WebSearchResult]: ...
    def first_result(self, query: str) -> WebSearchResult | None: ...
    def read_excerpt(self, url: str) -> str: ...


class _ArticleParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._skip_depth = 0
        self._paragraph_depth = 0
        self._paragraph_parts: list[str] = []
        self.paragraphs: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        lowered = tag.lower()
        if lowered in _SKIP_TAGS:
            self._skip_depth += 1
        if lowered == "p" and self._skip_depth == 0:
            self._paragraph_depth += 1
            if self._paragraph_depth == 1:
                self._paragraph_parts = []

    def handle_endtag(self, tag: str) -> None:
        lowered = tag.lower()
        if lowered == "p" and self._paragraph_depth:
            self._paragraph_depth -= 1
            if self._paragraph_depth == 0:
                paragraph = _clean_text(" ".join(self._paragraph_parts))
                if paragraph:
                    self.paragraphs.append(paragraph)
                self._paragraph_parts = []
        if lowered in _SKIP_TAGS and self._skip_depth:
            self._skip_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._skip_depth == 0 and self._paragraph_depth:
            self._paragraph_parts.append(data)


class BingResearchProvider:
    def __init__(self, *, timeout: float | None = None, client: httpx.Client | None = None) -> None:
        self.timeout = timeout if timeout is not None else _env_timeout()
        self.client = client or httpx.Client(timeout=self.timeout)

    def first_result(self, query: str) -> WebSearchResult | None:
        results = self.search_results(query, limit=1)
        return results[0] if results else None

    def search_results(self, query: str, *, limit: int = 5) -> list[WebSearchResult]:
        endpoint = "news/search" if _is_news_query(query) else "search"
        rss_url = f"https://www.bing.com/{endpoint}?format=rss&q={quote_plus(query.strip())}"
        response = self.client.get(rss_url, headers={"User-Agent": _user_agent()})
        response.raise_for_status()
        root = ElementTree.fromstring(response.content)
        candidates: list[tuple[int, WebSearchResult]] = []
        for index, item in enumerate(root.findall(".//item")):
            title = _clean_text(item.findtext("title") or "")
            url = _unwrap_bing_news_url((item.findtext("link") or "").strip())
            snippet = _clean_text(item.findtext("description") or "")
            published = _clean_text(item.findtext("pubDate") or "")
            if published:
                snippet = f"Published: {published}. {snippet}".strip()
            if not title or not is_safe_public_url(url) or _is_non_article_host(url):
                continue
            result = WebSearchResult(title=title, url=url, snippet=snippet)
            candidates.append((_result_score(result, index, query=query), result))
        candidates.sort(key=lambda item: item[0], reverse=True)
        return [result for _, result in candidates[:max(1, limit)]]

    def read_excerpt(self, url: str) -> str:
        response = self._safe_get(url)
        content_type = response.headers.get("content-type", "").lower()
        if "html" not in content_type and "xhtml" not in content_type:
            return ""
        return extract_article_excerpt(response.text)

    def _safe_get(self, url: str) -> httpx.Response:
        current = url
        for _ in range(5):
            if not is_safe_public_url(current):
                raise ValueError("The selected result is not a safe public web URL.")
            response = self.client.get(
                current,
                headers={"User-Agent": _user_agent()},
                follow_redirects=False,
            )
            if response.status_code not in {301, 302, 303, 307, 308}:
                response.raise_for_status()
                return response
            location = response.headers.get("location", "")
            if not location:
                response.raise_for_status()
            current = urljoin(current, location)
        raise ValueError("The selected page redirected too many times.")


def is_safe_public_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
        host = (parsed.hostname or "").strip("[]").lower()
        if parsed.scheme not in {"http", "https"} or not host:
            return False
        if parsed.username or parsed.password or host == "localhost" or host.endswith(".local"):
            return False
        if parsed.path.lower().endswith(_BLOCKED_SUFFIXES):
            return False
        try:
            address = ipaddress.ip_address(host)
        except ValueError:
            return True
        return not (
            address.is_private
            or address.is_loopback
            or address.is_link_local
            or address.is_multicast
            or address.is_reserved
        )
    except ValueError:
        return False


def _is_non_article_host(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower()
    return any(host == domain or host.endswith(f".{domain}") for domain in _NON_ARTICLE_HOSTS)


def _is_news_query(query: str) -> bool:
    lowered = str(query or "").lower()
    return any(signal in lowered for signal in ("latest", "news", "headline", "recent", "update"))


def _unwrap_bing_news_url(url: str) -> str:
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if host in {"bing.com", "www.bing.com"} and parsed.path.lower().endswith("/news/apiclick.aspx"):
        target = (parse_qs(parsed.query).get("url") or [""])[0].strip()
        if is_safe_public_url(target):
            return target
    return url


def _result_score(result: WebSearchResult, index: int, *, query: str = "") -> int:
    host = (urlparse(result.url).hostname or "").lower()
    score = max(0, 100 - index)
    freshness_requested = any(
        signal in query.lower()
        for signal in ("latest", "news", "headline", "current", "recent", "update")
    )
    for domain, weight in _PREFERRED_HOST_WEIGHTS.items():
        if host == domain or host.endswith(f".{domain}"):
            score += -180 if freshness_requested else weight
            break
    if host.endswith(".gov") or host.endswith(".edu"):
        score += 70
    lowered_title = result.title.lower()
    if "encyclopedia" in lowered_title or "official" in lowered_title:
        score += 30
    return score


def extract_article_excerpt(html: str, *, max_chars: int = 700) -> str:
    parser = _ArticleParser()
    parser.feed(str(html or ""))
    candidates = [paragraph for paragraph in parser.paragraphs if len(paragraph) >= 80]
    if not candidates:
        candidates = [paragraph for paragraph in parser.paragraphs if len(paragraph) >= 35]
    if not candidates:
        return ""
    paragraph = candidates[0]
    if len(paragraph) <= max_chars:
        return paragraph
    shortened = paragraph[:max_chars].rsplit(" ", 1)[0].rstrip(" ,;:")
    return f"{shortened}."


def _clean_text(value: str) -> str:
    cleaned = re.sub(r"\s+", " ", str(value or "")).strip()
    cleaned = re.sub(r"\s+([,.;:!?])", r"\1", cleaned)
    return cleaned.replace("( ", "(").replace(" )", ")")


def _user_agent() -> str:
    return "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126 Safari/537.36"


def _env_timeout() -> float:
    import os

    try:
        return max(2.0, float(os.getenv("FRIDAY_BROWSER_HTTP_TIMEOUT", "8")))
    except ValueError:
        return 8.0
