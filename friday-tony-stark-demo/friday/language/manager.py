from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .constants import DEFAULT_LANGUAGE, FALLBACK_LANGUAGE, SUPPORTED_LANGUAGES


def _deep_get(payload: dict[str, Any], key: str) -> Any:
    cursor: Any = payload
    for part in key.split("."):
        if not isinstance(cursor, dict) or part not in cursor:
            return None
        cursor = cursor[part]
    return cursor


@dataclass(slots=True)
class LanguageManager:
    base_dir: Path | None = None
    _cache: dict[str, dict[str, Any]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.base_dir is None:
            self.base_dir = Path(__file__).resolve().parent
        self._load_all()

    def _load_all(self) -> None:
        for lang in SUPPORTED_LANGUAGES:
            self._cache[lang] = self._load_language(lang)

    def _load_language(self, language: str) -> dict[str, Any]:
        folder = self.base_dir / language
        merged: dict[str, Any] = {}
        if not folder.exists():
            return merged
        for file in folder.glob("*.json"):
            merged[file.stem] = json.loads(file.read_text(encoding="utf-8"))
        return merged

    def get(self, key: str, *, language: str = DEFAULT_LANGUAGE, default: str = "") -> str:
        lang = language if language in SUPPORTED_LANGUAGES else DEFAULT_LANGUAGE
        value = _deep_get(self._cache.get(lang, {}), key)
        if value is None:
            value = _deep_get(self._cache.get(FALLBACK_LANGUAGE, {}), key)
        if value is None:
            return default
        return str(value)
