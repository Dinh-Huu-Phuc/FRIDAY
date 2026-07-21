"""App search scoring helpers."""

from __future__ import annotations

import re
import unicodedata
from difflib import SequenceMatcher

from friday.app.windows_launcher.schemas import AppMatch


def rank_apps(query: str, apps: list[AppMatch], limit: int) -> list[AppMatch]:
    normalized_query = normalize_text(query)
    if not normalized_query:
        return []

    scored: list[AppMatch] = []
    for app in apps:
        score = _score_app(normalized_query, app)
        if score <= 0:
            continue
        scored.append(app.model_copy(update={"score": round(score, 4)}))

    scored.sort(key=lambda item: (-item.score, item.name.casefold()))
    return scored[:limit]


def normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFD", value)
    ascii_value = "".join(char for char in normalized if unicodedata.category(char) != "Mn")
    ascii_value = re.sub(r"[^a-zA-Z0-9]+", " ", ascii_value).strip().casefold()
    return re.sub(r"\s+", " ", ascii_value)


def _score_app(normalized_query: str, app: AppMatch) -> float:
    candidates = [app.name]
    if app.app_id:
        candidates.append(app.app_id)
    if app.path:
        candidates.append(app.path)

    return max(_score_text(normalized_query, normalize_text(candidate)) for candidate in candidates)


def _score_text(query: str, candidate: str) -> float:
    if not candidate:
        return 0.0
    if candidate == query:
        return 1.0
    if candidate.startswith(query):
        return 0.92
    if query in candidate:
        return 0.84

    query_tokens = set(query.split())
    candidate_tokens = set(candidate.split())
    overlap = len(query_tokens & candidate_tokens) / max(1, len(query_tokens))
    similarity = SequenceMatcher(None, query, candidate).ratio()

    if overlap:
        return max(0.62 + overlap * 0.25, similarity * 0.8)
    if similarity >= 0.45:
        return similarity * 0.72
    return 0.0
