from __future__ import annotations

import re

from friday.app.code_map.schemas import CodeMapAction, CodeMapIntentMatch


_ACTION_BY_VERB = {
    "open": CodeMapAction.OPEN,
    "show": CodeMapAction.OPEN,
    "launch": CodeMapAction.OPEN,
    "display": CodeMapAction.OPEN,
    "close": CodeMapAction.CLOSE,
    "hide": CodeMapAction.CLOSE,
    "dismiss": CodeMapAction.CLOSE,
}
_COMMAND_PATTERN = re.compile(
    r"^(?:(?:hey\s+)?friday\s+)?"
    r"(?:(?:please|kindly)\s+)?"
    r"(?:(?:can|could|would|will)\s+you\s+)?"
    r"(?:(?:please|kindly)\s+)?"
    r"(?P<verb>open|show|launch|display|close|hide|dismiss)\s+"
    r"(?:the\s+)?(?:code\s+map|codemap)"
    r"(?:\s+(?:please|for\s+me))?$"
)


def normalize_code_map_phrase(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", " ", str(value or "").lower()).strip()
    return re.sub(r"\s+", " ", normalized)


def match_code_map_intent(message: str) -> CodeMapIntentMatch:
    matched = _COMMAND_PATTERN.fullmatch(normalize_code_map_phrase(message))
    if matched is None:
        return CodeMapIntentMatch()
    verb = matched.group("verb")
    return CodeMapIntentMatch(
        action=_ACTION_BY_VERB[verb],
        trigger_id=f"code_map_{verb}",
    )
