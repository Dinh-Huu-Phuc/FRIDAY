from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class CameraWindowAction(str, Enum):
    NONE = "none"
    OPEN = "open"
    CLOSE = "close"
    ANALYZE = "analyze"
    LOCATE = "locate"
    SEGMENT = "segment"
    TRACK_MASK = "track_mask"
    STOP_MASK_TRACKING = "stop_mask_tracking"
    CLEAR_MASK = "clear_mask"


@dataclass(frozen=True, slots=True)
class CameraWindowIntentMatch:
    action: CameraWindowAction = CameraWindowAction.NONE
    trigger_id: str = ""
    query: str = ""


@dataclass(frozen=True, slots=True)
class CameraWindowCommandResult:
    handled: bool
    accepted: bool = False
    action: CameraWindowAction = CameraWindowAction.NONE
    message: str = ""
    query: str = ""
