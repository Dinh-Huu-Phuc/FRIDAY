from __future__ import annotations

import re

from friday.app.code_map.schemas import CodeMapAction, CodeMapIntentMatch


_PHRASES = {
    "open code map": (CodeMapAction.OPEN, "open_default"),
    "friday open code map": (CodeMapAction.OPEN, "open_friday"),
    "show code map": (CodeMapAction.OPEN, "show_default"),
    "friday show code map": (CodeMapAction.OPEN, "show_friday"),
    "friday launch code map": (CodeMapAction.OPEN, "launch_friday"),
    "close code map": (CodeMapAction.CLOSE, "close_default"),
    "friday close code map": (CodeMapAction.CLOSE, "close_friday"),
    "hide code map": (CodeMapAction.CLOSE, "hide_default"),
    "friday hide code map": (CodeMapAction.CLOSE, "hide_friday"),
    "friday close the code map": (CodeMapAction.CLOSE, "close_the_map"),
}


def normalize_code_map_phrase(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", " ", str(value or "").lower()).strip()
    return re.sub(r"\s+", " ", normalized)


def match_code_map_intent(message: str) -> CodeMapIntentMatch:
    matched = _PHRASES.get(normalize_code_map_phrase(message))
    if matched is None:
        return CodeMapIntentMatch()
    action, trigger_id = matched
    return CodeMapIntentMatch(action=action, trigger_id=trigger_id)
