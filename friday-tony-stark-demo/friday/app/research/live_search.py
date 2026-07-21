"""Server-side public web search that never opens the user's browser."""

from __future__ import annotations

import os
import re
from concurrent.futures import ThreadPoolExecutor

from friday.app.browser_automation.reader import BingResearchProvider, ResearchProvider

from .schemas import LiveSearchResult, LiveSearchSource


def search_public_web(
    query: str,
    *,
    provider: ResearchProvider | None = None,
    max_sources: int | None = None,
) -> LiveSearchResult:
    normalized_query = " ".join(str(query or "").split()).strip()
    if not normalized_query or len(normalized_query) > 300:
        return LiveSearchResult(False, normalized_query, "The live-search query is empty or too long.")

    source_limit = max_sources if max_sources is not None else _max_sources()
    source_limit = max(1, min(5, int(source_limit)))
    search_query = optimize_search_query(normalized_query)
    active_provider = provider or BingResearchProvider()
    try:
        candidates = active_provider.search_results(
            search_query,
            limit=max(source_limit * 2, 5),
        )
    except Exception:
        return LiveSearchResult(
            False,
            normalized_query,
            "Live Search could not reach the public search service.",
        )

    eligible = []
    seen_urls: set[str] = set()
    for candidate in candidates:
        if not is_relevant_search_result(candidate, search_query):
            continue
        if candidate.url in seen_urls:
            continue
        seen_urls.add(candidate.url)
        eligible.append(candidate)

    def read_excerpt(candidate):
        try:
            return active_provider.read_excerpt(candidate.url)
        except Exception:
            return ""

    worker_count = min(5, len(eligible))
    if worker_count:
        with ThreadPoolExecutor(
            max_workers=worker_count,
            thread_name_prefix="friday-live-search",
        ) as executor:
            excerpts = list(executor.map(read_excerpt, eligible))
    else:
        excerpts = []

    sources: list[LiveSearchSource] = []
    for candidate, excerpt in zip(eligible, excerpts):
        cleaned_excerpt = " ".join(str(excerpt or "").split()).strip()
        if not cleaned_excerpt:
            continue
        sources.append(
            LiveSearchSource(
                title=" ".join(candidate.title.split())[:240],
                url=candidate.url,
                excerpt=cleaned_excerpt[:1200],
            )
        )
        if len(sources) >= source_limit:
            break

    if not sources:
        return LiveSearchResult(
            False,
            normalized_query,
            f"I searched for {normalized_query}, but no safe readable source was available.",
            candidate_count=len(candidates),
        )

    return LiveSearchResult(
        True,
        search_query,
        f"Live Search read {len(sources)} public source{'s' if len(sources) != 1 else ''}.",
        sources=tuple(sources),
        candidate_count=len(candidates),
    )


def optimize_search_query(query: str) -> str:
    candidate = " ".join(str(query or "").strip(" \t\r\n.,!?;:\"'").split())
    lowered = candidate.lower()
    patterns = (
        r"^(?:who|what)\s+is\s+(?:the\s+)?current\s+(?P<role>.+?)\s+of\s+(?P<entity>.+)$",
        r"^current\s+(?P<role>ceo|president|chairman|owner|director)\s+(?:of\s+)?(?P<entity>.+)$",
    )
    for pattern in patterns:
        match = re.match(pattern, candidate, flags=re.IGNORECASE)
        if match:
            return f"{match.group('entity')} current {match.group('role')}"

    latest = re.match(
        r"^(?:(?:what|who)\s+is\s+(?:the\s+)?)?"
        r"(?P<signal>latest|recent|current)\s+(?P<subject>.+)$",
        candidate,
        flags=re.IGNORECASE,
    )
    if latest:
        subject = re.sub(r"\s+official$", "", latest.group("subject"), flags=re.IGNORECASE)
        return f"{subject} {latest.group('signal').lower()}"

    if lowered.startswith(("who is ", "what is ", "where is ", "when did ")):
        return re.sub(
            r"^(?:who|what|where)\s+is\s+(?:the\s+)?|^when\s+did\s+",
            "",
            candidate,
            count=1,
            flags=re.IGNORECASE,
        )
    return candidate


def is_relevant_search_result(candidate, query: str) -> bool:
    stopwords = {
        "about", "and", "current", "find", "for", "information", "latest",
        "look", "news", "official", "recent", "the", "today", "update",
    }
    terms = {
        token
        for token in re.findall(r"[a-z0-9]+", query.lower())
        if len(token) >= 3 and token not in stopwords
    }
    if not terms:
        return True
    haystack = " ".join(
        (str(candidate.title or ""), str(candidate.snippet or ""), str(candidate.url or ""))
    ).lower()
    return any(term in haystack for term in terms)


def _max_sources() -> int:
    try:
        return int(os.getenv("FRIDAY_LIVE_SEARCH_MAX_SOURCES", "3"))
    except ValueError:
        return 3
