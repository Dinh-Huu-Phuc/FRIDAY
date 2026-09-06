from __future__ import annotations

import re

from friday.app.perception.segmentation.schemas import (
    SegmentationIntentAction,
    SegmentationIntentMatch,
)

_STOP_PATTERNS = (
    r"^(?:friday )?(?:please )?stop (?:the )?(?:precise )?mask tracking$",
    r"^(?:friday )?(?:please )?stop tracking (?:the )?(?:object )?mask$",
    r"^(?:friday )?(?:please )?stop segmentation tracking$",
)

_CLEAR_PATTERNS = (
    r"^(?:friday )?(?:please )?(?:clear|hide|remove) (?:the )?(?:segmentation )?mask$",
    r"^(?:friday )?(?:please )?clear segmentation$",
)

_TRACK_PATTERNS = (
    (
        "precise_mask_tracking",
        re.compile(
            r"^(?:friday )?(?:please )?(?:precisely track|start precise tracking (?:of|for)) "
            r"(?:the )?(?P<target>.+?)(?: (?:in|with|through) (?:the )?(?:camera|webcam))?$"
        ),
    ),
    (
        "track_object_mask",
        re.compile(
            r"^(?:friday )?(?:please )?track (?:the )?(?P<target>.+?) "
            r"(?:object )?mask(?: (?:in|with|through) (?:the )?(?:camera|webcam))?$"
        ),
    ),
)

_SEGMENT_PATTERNS = (
    (
        "segment_camera_object",
        re.compile(
            r"^(?:friday )?(?:please )?(?:segment|outline|isolate) (?:the )?"
            r"(?P<target>.+?)(?: (?:in|from|with|through) (?:the )?"
            r"(?:camera|webcam)(?: view| scene)?)?$"
        ),
    ),
    (
        "segment_current_target",
        re.compile(
            r"^(?:friday )?(?:please )?(?:segment|outline) "
            r"(?:the )?(?P<target>current target|locked target)$"
        ),
    ),
)


def normalize_segmentation_phrase(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", " ", str(value or "").lower()).strip()
    normalized = re.sub(r"^friday\s+agent\b", "friday", normalized)
    return re.sub(r"\s+", " ", normalized).strip()


def match_segmentation_intent(message: str) -> SegmentationIntentMatch:
    normalized = normalize_segmentation_phrase(message)
    for pattern in _STOP_PATTERNS:
        if re.fullmatch(pattern, normalized):
            return SegmentationIntentMatch(
                action=SegmentationIntentAction.STOP,
                trigger_id="stop_mask_tracking",
            )
    for pattern in _CLEAR_PATTERNS:
        if re.fullmatch(pattern, normalized):
            return SegmentationIntentMatch(
                action=SegmentationIntentAction.CLEAR,
                trigger_id="clear_segmentation_mask",
            )
    for trigger_id, pattern in _TRACK_PATTERNS:
        matched = pattern.fullmatch(normalized)
        if matched is not None:
            if not _is_camera_specific(normalized):
                continue
            return SegmentationIntentMatch(
                action=SegmentationIntentAction.TRACK,
                target=_clean_target(matched.group("target")),
                trigger_id=trigger_id,
            )
    for trigger_id, pattern in _SEGMENT_PATTERNS:
        matched = pattern.fullmatch(normalized)
        if matched is not None:
            target = _clean_target(matched.group("target"))
            if not _is_camera_specific(normalized) and target not in {
                "current target",
                "locked target",
            }:
                continue
            if target in {"current target", "locked target"}:
                target = ""
            return SegmentationIntentMatch(
                action=SegmentationIntentAction.SEGMENT,
                target=target,
                trigger_id=trigger_id,
            )
    return SegmentationIntentMatch()


def _clean_target(value: str) -> str:
    target = re.sub(r"^(?:the|a|an|my)\s+", "", value.strip())
    target = re.sub(r"\s+(?:please|for me)$", "", target).strip()
    return target[:100]


def _is_camera_specific(normalized: str) -> bool:
    return (
        normalized.startswith("friday ")
        or " camera" in normalized
        or " webcam" in normalized
        or " mask" in normalized
    )
