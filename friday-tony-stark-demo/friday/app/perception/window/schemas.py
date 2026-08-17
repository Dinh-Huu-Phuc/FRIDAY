from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class CameraWindowAction(str, Enum):
    NONE = "none"
    OPEN = "open"
    CLOSE = "close"
    ANALYZE = "analyze"


@dataclass(frozen=True, slots=True)
class CameraWindowIntentMatch:
    action: CameraWindowAction = CameraWindowAction.NONE
    trigger_id: str = ""


@dataclass(frozen=True, slots=True)
class CameraWindowCommandResult:
    handled: bool
    accepted: bool = False
    action: CameraWindowAction = CameraWindowAction.NONE
    message: str = ""
