"""Pydantic entities for the computer module."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ActionType(str, Enum):
    CLICK = "click"
    DOUBLE_CLICK = "double_click"
    RIGHT_CLICK = "right_click"
    TYPE = "type"
    PRESS = "press"
    HOTKEY = "hotkey"
    SCROLL = "scroll"
    DRAG = "drag"
    SHELL = "shell"
    OBSERVE = "observe"


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SafetyMode(str, Enum):
    STRICT = "strict"
    MODERATE = "moderate"
    OFF = "off"


class SafetyCheckResult(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    allowed: bool
    risk_level: RiskLevel
    reason: str


class ScreenImage(BaseModel):
    monitor_index: int
    screenshot_path: str
    compressed_screenshot_path: str | None = None
    is_active: bool = False
    left: int = 0
    top: int = 0
    width: int
    height: int


class ScreenObservation(BaseModel):
    screenshot_path: str
    compressed_screenshot_path: str | None = None
    active_window_title: str = ""
    screen_width: int
    screen_height: int
    capture_scope: str = "virtual"
    screen_images: list[ScreenImage] = Field(default_factory=list)
    observed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    notes: list[str] = Field(default_factory=list)


class ComputerAction(BaseModel):
    model_config = ConfigDict(populate_by_name=True, use_enum_values=True)

    action_type: ActionType = Field(alias="type")
    description: str = ""
    target: str | None = None
    x: int | None = None
    y: int | None = None
    end_x: int | None = None
    end_y: int | None = None
    button: str = "left"
    text: str | None = None
    key: str | None = None
    keys: list[str] = Field(default_factory=list)
    amount: int | None = None
    command: str | None = None
    timeout: int = 20
    rationale: str = ""


class RuntimeContextSnapshot(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    current_goal: str = ""
    current_plan: list[str] = Field(default_factory=list)
    last_action: dict[str, Any] | None = None
    active_window_title: str = ""
    last_screenshot_path: str = ""
    screen_width: int = 0
    screen_height: int = 0
    safety_mode: SafetyMode = SafetyMode.STRICT
