from __future__ import annotations

import re
import unicodedata

from friday.about.loader_about import load_self_intro_document
from friday.about.schemas_about import AboutMatch


SELF_INTRO_FALLBACK_TRIGGERS = (
    "introduce yourself",
    "who are you",
    "what can you do",
    "tell me about yourself",
    "tell me about friday",
)


def normalize_about_text(value: str) -> str:
    decomposed = unicodedata.normalize("NFD", value or "")
    without_marks = "".join(
        character for character in decomposed if unicodedata.category(character) != "Mn"
    )
    return " ".join(without_marks.lower().split())


def _phrase_matches(message: str, phrase: str) -> bool:
    normalized_message = normalize_about_text(message)
    normalized_phrase = normalize_about_text(phrase)
    if not normalized_phrase:
        return False
    if normalized_phrase in normalized_message:
        return True
    words = [word for word in re.split(r"\W+", normalized_phrase) if len(word) >= 3]
    if len(words) < 2:
        return False
    return all(word in normalized_message for word in words)


def is_self_intro_request(message: str) -> bool:
    document = load_self_intro_document()
    triggers = (*document.triggers, *SELF_INTRO_FALLBACK_TRIGGERS)
    return any(_phrase_matches(message, trigger) for trigger in triggers)


def get_friday_self_intro(response_type: str = "voice") -> str:
    document = load_self_intro_document()
    key = normalize_about_text(response_type).replace(" ", "_") or "voice"
    return (
        document.responses.get(key)
        or document.responses.get("voice")
        or document.responses.get("short")
        or document.responses.get("full")
        or ""
    ).strip()


def match_about_response(message: str, *, response_type: str = "voice") -> AboutMatch:
    if not is_self_intro_request(message):
        return AboutMatch(matched=False, response_type=response_type)
    return AboutMatch(
        matched=True,
        document_id=load_self_intro_document().id,
        response_type=response_type,
        response=get_friday_self_intro(response_type),
        trigger="self_intro",
    )
