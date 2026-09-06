from __future__ import annotations

import re

from friday.app.perception.detection.grounding.schemas import GroundingIntentMatch

_GROUNDING_PATTERNS = (
    (
        "camera_find",
        re.compile(
            r"^(?:friday )?(?:please )?(?:find|locate|look for) "
            r"(?P<query>.+?) (?:in|using|with|through) "
            r"(?:the )?(?:camera|webcam)(?: view| scene)?$"
        ),
    ),
    (
        "camera_find_prefix",
        re.compile(
            r"^(?:friday )?(?:please )?(?:use )?(?:the )?"
            r"(?:camera|webcam) (?:to )?(?:find|locate|look for) (?P<query>.+)$"
        ),
    ),
    (
        "camera_where",
        re.compile(
            r"^(?:friday )?(?:please )?(?:show me )?where (?:is|are) "
            r"(?P<query>.+?) (?:in|on|through) "
            r"(?:the )?(?:camera|webcam)(?: view| scene)?$"
        ),
    ),
    (
        "visual_find",
        re.compile(
            r"^(?:friday )?(?:please )?(?:visually find|visually locate) "
            r"(?P<query>.+)$"
        ),
    ),
)


def normalize_grounding_phrase(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", " ", str(value or "").lower()).strip()
    normalized = re.sub(r"^friday\s+agent\b", "friday", normalized)
    return re.sub(r"\s+", " ", normalized).strip()


def match_grounding_intent(message: str) -> GroundingIntentMatch:
    normalized = normalize_grounding_phrase(message)
    for trigger_id, pattern in _GROUNDING_PATTERNS:
        matched = pattern.fullmatch(normalized)
        if matched is None:
            continue
        query = _clean_query(matched.group("query"))
        if query:
            return GroundingIntentMatch(
                matched=True,
                query=query,
                trigger_id=trigger_id,
            )
    return GroundingIntentMatch()


def _clean_query(value: str) -> str:
    query = re.sub(r"^(?:the|a|an|my)\s+", "", value.strip())
    query = re.sub(r"\s+(?:please|for me)$", "", query).strip()
    return query[:150]
