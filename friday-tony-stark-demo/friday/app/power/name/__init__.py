"""Exact phrase matching and responses for FRIDAY power commands."""

from .aliases import PHRASE_SPECS, PhraseSpec
from .matcher import match_power_phrase
from .responses import select_power_response

__all__ = [
    "PHRASE_SPECS",
    "PhraseSpec",
    "match_power_phrase",
    "select_power_response",
]

