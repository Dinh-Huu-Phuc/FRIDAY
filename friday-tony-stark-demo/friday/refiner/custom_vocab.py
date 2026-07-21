from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Iterable


@dataclass(slots=True)
class VocabularyProfile:
    keywords: list[str] = field(default_factory=list)
    alias_map: dict[str, str] = field(default_factory=dict)


def default_vocabulary_profile() -> VocabularyProfile:
    return VocabularyProfile(
        keywords=[
            "Friday", "F.R.I.D.A.Y.", "Jarvis", "Tony Stark", "Smart Home",
            "living room", "bedroom", "kitchen", "bathroom", "garage",
            "temperature", "humidity", "close the door", "open the door",
            "turn on the lights", "turn off the lights", "turn on the fan", "turn off the fan",
        ],
        alias_map={
            "fridai": "Friday", "fri day": "Friday", "f r i d a y": "Friday",
            "jar vis": "Jarvis", "smarthome": "Smart Home", "smart hom": "Smart Home",
            "smart homee": "Smart Home", "toney stark": "Tony Stark", "toni stark": "Tony Stark",
        },
    )


def merge_vocabulary(
    base: VocabularyProfile,
    extra_keywords: Iterable[str] | None = None,
    extra_aliases: dict[str, str] | None = None,
) -> VocabularyProfile:
    keywords = list(base.keywords)
    alias_map = dict(base.alias_map)
    for item in extra_keywords or ():
        word = str(item).strip()
        if word and word not in keywords:
            keywords.append(word)
    for key, value in (extra_aliases or {}).items():
        alias_key = str(key).strip().lower()
        alias_value = str(value).strip()
        if alias_key and alias_value:
            alias_map[alias_key] = alias_value
    return VocabularyProfile(keywords=keywords, alias_map=alias_map)


def build_vocabulary_context_text(profile: VocabularyProfile) -> str:
    lines = ["- keywords:", *(f"  - {keyword}" for keyword in profile.keywords), "- alias_map:"]
    lines.extend(
        (f"  - {wrong} -> {correct}" for wrong, correct in profile.alias_map.items())
        if profile.alias_map
        else ("  - none",)
    )
    return "\n".join(lines)


def normalize_with_aliases(text: str, profile: VocabularyProfile) -> str:
    normalized = text
    for wrong, correct in profile.alias_map.items():
        normalized = re.sub(rf"(?i)\b{re.escape(wrong)}\b", correct, normalized)
    return normalize_identifier_tokens(normalized)


def normalize_identifier_tokens(text: str) -> str:
    """Normalize simple ID and token-like strings for stable downstream prompts."""
    cleaned = str(text or "")
    cleaned = re.sub(r"\b([A-Za-z])\s*-\s*(\d+)\b", r"\1\2", cleaned)
    cleaned = re.sub(r"\b(id|code)\s*[:=]\s*([A-Za-z0-9_-]{3,})\b", r"\1 \2", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\b(token|secret|apikey)\s*[:=]\s*([A-Za-z0-9._-]{6,})\b", r"\1 \2", cleaned, flags=re.IGNORECASE)
    return cleaned
