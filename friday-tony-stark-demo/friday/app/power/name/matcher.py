"""Strict whole-phrase matcher for FRIDAY power commands."""

from __future__ import annotations

import re

from ..types import PowerIntentMatch
from .aliases import PHRASE_SPECS


def normalize_power_phrase(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", " ", str(value or "").lower()).strip()
    return re.sub(r"\s+", " ", normalized)


_PHRASE_INDEX = {
    normalize_power_phrase(spec.phrase): spec
    for spec in PHRASE_SPECS
}


def match_power_phrase(message: str) -> PowerIntentMatch:
    """Return a match only when the entire message is allowlisted."""
    spec = _PHRASE_INDEX.get(normalize_power_phrase(message))
    if spec is None:
        return PowerIntentMatch()
    return PowerIntentMatch(
        intent=spec.intent,
        trigger_id=spec.trigger_id,
        response_group=spec.response_group,
    )
