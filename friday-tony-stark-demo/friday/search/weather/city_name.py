"""
Vietnam city resolver backed by the full local OpenWeather city database.
"""

from __future__ import annotations

import json
import re
import unicodedata
from functools import lru_cache
from pathlib import Path
from typing import Any

DB_PATH = Path(__file__).resolve().parent / "db" / "vietnam_cities_list.json"

DISPLAY_NAME_OVERRIDES = {
    "Da Lat": "Da Lat",
    "Ha Noi": "Hanoi",
    "Thanh pho Ho Chi Minh": "Ho Chi Minh City",
    "Can Tho": "Can Tho",
    "Hue": "Hue",
    "Vung Tau": "Vung Tau",
    "Buon Ma Thuot": "Buon Ma Thuot",
    "Bien Hoa": "Bien Hoa",
    "Bac Giang": "Bac Giang",
    "Bac Kan": "Bac Kan",
    "Bac Ninh": "Bac Ninh",
    "Ben Tre": "Ben Tre",
    "Ca Mau": "Ca Mau",
    "Dien Bien Phu": "Dien Bien Phu",
    "Ha Tinh": "Ha Tinh",
    "Quy Nhon": "Quy Nhon",
    "Rach Gia": "Rach Gia",
    "Soc Trang": "Soc Trang",
    "Vinh Long": "Vinh Long",
    "Vinh Yen": "Vinh Yen",
    "My Tho": "My Tho",
    "Phan Rang-Thap Cham": "Phan Rang - Thap Cham",
    "Phan Thiet": "Phan Thiet",
    "Thai Nguyen": "Thai Nguyen",
    "Tuy Hoa": "Tuy Hoa",
}

MANUAL_ALIASES = {
    "hanoi": "Ha Noi",
    "ha noi": "Ha Noi",
    "hn": "Ha Noi",
    "ho chi minh": "Thanh pho Ho Chi Minh",
    "ho chi minh city": "Thanh pho Ho Chi Minh",
    "hcm": "Thanh pho Ho Chi Minh",
    "hcmc": "Thanh pho Ho Chi Minh",
    "sai gon": "Thanh pho Ho Chi Minh",
    "saigon": "Thanh pho Ho Chi Minh",
    "da lat": "Da Lat",
    "dalat": "Da Lat",
    "can tho": "Can Tho",
    "cantho": "Can Tho",
    "hue": "Hue",
    "nha trang": "Nha Trang",
    "nhatrang": "Nha Trang",
    "vung tau": "Vung Tau",
    "vungtau": "Vung Tau",
    "buon ma thuot": "Buon Ma Thuot",
    "bmt": "Buon Ma Thuot",
    "bien hoa": "Bien Hoa",
    "bienhoa": "Bien Hoa",
    "quy nhon": "Quy Nhon",
    "quynhon": "Quy Nhon",
    "rach gia": "Rach Gia",
    "rachgia": "Rach Gia",
    "soc trang": "Soc Trang",
    "soctrang": "Soc Trang",
    "my tho": "My Tho",
    "mytho": "My Tho",
    "thai nguyen": "Thai Nguyen",
    "thainguyen": "Thai Nguyen",
    "tuy hoa": "Tuy Hoa",
    "tuyhoa": "Tuy Hoa",
    "lam dong": "Da Lat",
    "dong nai": "Bien Hoa",
    "dak lak": "Buon Ma Thuot",
    "daklak": "Buon Ma Thuot",
    "khanh hoa": "Nha Trang",
    "gia lai": "Pleiku",
    "an giang": "Long Xuyen",
    "kien giang": "Rach Gia",
    "ba ria vung tau": "Vung Tau",
    "ba ria - vung tau": "Vung Tau",
}

STOP_WORDS = {
    "city",
    "town",
    "province",
}

LOW_PRIORITY_PREFIXES: tuple[str, ...] = ()


def _strip_accents(value: str) -> str:
    normalized = unicodedata.normalize("NFD", value or "")
    stripped = "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")
    return stripped


def _normalize_text(value: str) -> str:
    stripped = _strip_accents(value or "").casefold()
    stripped = re.sub(r"[^a-z0-9]+", " ", stripped)
    return re.sub(r"\s+", " ", stripped).strip()


def _collapse_text(value: str) -> str:
    return _normalize_text(value).replace(" ", "")


def _remove_stop_words(value: str) -> str:
    tokens = [token for token in _normalize_text(value).split() if token not in STOP_WORDS]
    return " ".join(tokens).strip()


def _add_aliases(target: set[str], value: str) -> None:
    if not value:
        return

    normalized = _normalize_text(value)
    if normalized:
        target.add(normalized)

    collapsed = normalized.replace(" ", "")
    if collapsed:
        target.add(collapsed)

    without_stop_words = _remove_stop_words(value)
    if without_stop_words:
        target.add(without_stop_words)
        target.add(without_stop_words.replace(" ", ""))


def _entry_priority(name: str) -> int:
    normalized = _normalize_text(name)
    if normalized.startswith(LOW_PRIORITY_PREFIXES):
        return -20
    return 0


@lru_cache(maxsize=1)
def load_vietnam_city_entries() -> list[dict[str, Any]]:
    """
    Load every location entry from the local JSON database.
    """
    raw_entries = json.loads(DB_PATH.read_text(encoding="utf-8"))
    processed_entries: list[dict[str, Any]] = []

    for item in raw_entries:
        name = str(item.get("name", "")).strip()
        coord = item.get("coord") or {}
        display_name = DISPLAY_NAME_OVERRIDES.get(name, name)
        aliases: set[str] = set()

        _add_aliases(aliases, name)
        _add_aliases(aliases, display_name)
        _add_aliases(aliases, item.get("state") or "")

        processed_entries.append(
            {
                "id": item.get("id"),
                "name": name,
                "display_name": display_name,
                "state": item.get("state") or "",
                "country": item.get("country") or "VN",
                "lat": coord.get("lat"),
                "lon": coord.get("lon"),
                "aliases": aliases,
                "priority": _entry_priority(name),
            }
        )

    by_name = {entry["name"]: entry for entry in processed_entries}
    for alias, canonical_name in MANUAL_ALIASES.items():
        entry = by_name.get(canonical_name)
        if entry:
            _add_aliases(entry["aliases"], alias)

    return processed_entries


def _query_variants(query: str) -> list[str]:
    normalized = _normalize_text(query)
    collapsed = normalized.replace(" ", "")
    without_stop_words = _remove_stop_words(query)
    variants = [normalized, collapsed, without_stop_words, without_stop_words.replace(" ", "")]
    return [variant for variant in variants if variant]


def _score_entry(entry: dict[str, Any], query_variants: list[str]) -> int:
    aliases: set[str] = entry["aliases"]
    best_score = entry["priority"]

    for query in query_variants:
        if not query:
            continue

        if query in aliases:
            best_score = max(best_score, 300 + entry["priority"])

        for alias in aliases:
            if not alias:
                continue
            if query == alias:
                best_score = max(best_score, 300 + entry["priority"])
            elif len(query) >= 4 and alias.startswith(query):
                best_score = max(best_score, 220 + entry["priority"])
            elif len(query) >= 4 and query in alias:
                best_score = max(best_score, 180 + entry["priority"])
            elif len(alias) >= 4 and alias in query:
                best_score = max(best_score, 160 + entry["priority"])
            else:
                query_tokens = set(query.split())
                alias_tokens = set(alias.split())
                overlap = len(query_tokens & alias_tokens)
                if overlap:
                    best_score = max(best_score, overlap * 20 + entry["priority"])

    return best_score


def resolve_vietnam_city(query: str) -> dict[str, Any] | None:
    """
    Resolve a user-entered Vietnamese place name to a local city entry with coordinates.
    """
    query = (query or "").strip()
    if not query:
        return None

    query_variants = _query_variants(query)
    if not query_variants:
        return None

    best_entry: dict[str, Any] | None = None
    best_score = -999

    for entry in load_vietnam_city_entries():
        score = _score_entry(entry, query_variants)
        if score > best_score:
            best_entry = entry
            best_score = score

    if not best_entry or best_score < 80:
        return None

    return {
        "id": best_entry["id"],
        "name": best_entry["name"],
        "display_name": best_entry["display_name"],
        "state": best_entry["state"],
        "country": best_entry["country"],
        "lat": best_entry["lat"],
        "lon": best_entry["lon"],
    }
