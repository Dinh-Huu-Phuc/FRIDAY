from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class LanguageState:
    current_language: str
    fallback_language: str


@dataclass(slots=True)
class UserLanguagePreference:
    user_id: str
    language: str
    persistent: bool = False


@dataclass(slots=True)
class LanguageDetectionResult:
    should_switch: bool
    language: str | None = None
    persistent: bool = False
