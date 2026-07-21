"""Shared types for FRIDAY power commands."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class PowerIntent(str, Enum):
    NONE = "none"
    SLEEP = "sleep"
    WAKE = "wake"


@dataclass(frozen=True, slots=True)
class PowerIntentMatch:
    intent: PowerIntent = PowerIntent.NONE
    trigger_id: str = ""
    response_group: str = ""

