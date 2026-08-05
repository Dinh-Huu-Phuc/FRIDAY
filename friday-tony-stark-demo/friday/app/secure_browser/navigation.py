from __future__ import annotations

from urllib.parse import quote_plus, urlparse


FRIDAY_HOME_URL = "friday://home"
GOOGLE_SEARCH_URL = "https://www.google.com/search?q={query}"


def google_search_url(query: str) -> str:
    normalized = " ".join(str(query or "").split()).strip()
    return GOOGLE_SEARCH_URL.format(query=quote_plus(normalized))


def navigation_url(value: str) -> str:
    candidate = str(value or "").strip()
    if not candidate:
        return FRIDAY_HOME_URL
    if candidate in {"about:blank", FRIDAY_HOME_URL}:
        return candidate

    parsed = urlparse(candidate)
    if parsed.scheme in {"http", "https"} and parsed.netloc:
        return candidate

    if " " not in candidate and (
        "." in candidate
        or candidate.lower().startswith("localhost")
        or candidate.startswith("127.0.0.1")
    ):
        return f"https://{candidate}"

    return google_search_url(candidate)
