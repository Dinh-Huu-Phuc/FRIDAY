from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class CodeMapAction(str, Enum):
    NONE = "none"
    OPEN = "open"
    CLOSE = "close"


@dataclass(frozen=True, slots=True)
class CodeMapIntentMatch:
    action: CodeMapAction = CodeMapAction.NONE
    trigger_id: str = ""


@dataclass(frozen=True, slots=True)
class CodeMapCommandResult:
    handled: bool
    accepted: bool = False
    action: CodeMapAction = CodeMapAction.NONE
    message: str = ""
