"""Action execution service for the computer module."""

from __future__ import annotations

from typing import Any

from friday.app.computer.config.settings import ComputerSettings
from friday.app.computer.exceptions import ComputerExecutionError
from friday.app.computer.schemas.entities import ActionType, ComputerAction, RiskLevel, SafetyCheckResult, SafetyMode
from friday.tools.computer import keyboard as keyboard_tools
from friday.tools.computer import mouse as mouse_tools
from friday.tools.computer import terminal as terminal_tools
from friday.tools.computer.safety import validate_command
from friday.tools.computer import vision


class ComputerExecutor:
    def __init__(self, *, settings: ComputerSettings) -> None:
        self.settings = settings

    def execute_action(
        self,
        action: ComputerAction,
        *,
        safety_mode: SafetyMode | str | None = None,
    ) -> tuple[SafetyCheckResult, bool, dict[str, Any], str]:
        mode = self._normalize_safety_mode(safety_mode)
        safety = self._validate_action(action, mode)
        if not safety.allowed:
            return safety, False, {}, safety.reason

        try:
            if action.action_type == ActionType.OBSERVE:
                return safety, False, {"status": "no-op"}, "Observation step does not execute input."

            if action.action_type == ActionType.CLICK:
                mouse_tools.move_to(action.x, action.y, duration=self.settings.mouse_duration)
                result = mouse_tools.click(action.x, action.y)
                return safety, True, result, "Click executed."

            if action.action_type == ActionType.DOUBLE_CLICK:
                mouse_tools.move_to(action.x, action.y, duration=self.settings.mouse_duration)
                result = mouse_tools.double_click(action.x, action.y)
                return safety, True, result, "Double click executed."

            if action.action_type == ActionType.RIGHT_CLICK:
                mouse_tools.move_to(action.x, action.y, duration=self.settings.mouse_duration)
                result = mouse_tools.right_click(action.x, action.y)
                return safety, True, result, "Right click executed."

            if action.action_type == ActionType.TYPE:
                result = keyboard_tools.type_text(action.text or "", interval=self.settings.type_interval)
                return safety, True, result, "Text typed."

            if action.action_type == ActionType.PRESS:
                result = keyboard_tools.press(action.key or "")
                return safety, True, result, "Key pressed."

            if action.action_type == ActionType.HOTKEY:
                result = keyboard_tools.hotkey(*(action.keys or []))
                return safety, True, result, "Hotkey executed."

            if action.action_type == ActionType.SCROLL:
                result = mouse_tools.scroll(action.amount or 0)
                return safety, True, result, "Scroll executed."

            if action.action_type == ActionType.DRAG:
                mouse_tools.move_to(action.x, action.y, duration=self.settings.mouse_duration)
                result = mouse_tools.drag_to(
                    action.end_x,
                    action.end_y,
                    start_x=action.x,
                    start_y=action.y,
                    duration=self.settings.mouse_duration,
                )
                return safety, True, result, "Drag executed."

            if action.action_type == ActionType.SHELL:
                result = terminal_tools.run_command(
                    action.command or "",
                    timeout=action.timeout or self.settings.default_command_timeout,
                    safety_mode=mode.value,
                )
                shell_safety = SafetyCheckResult.model_validate(result["safety"])
                return (
                    shell_safety,
                    bool(result["ok"]) and shell_safety.allowed,
                    result,
                    "Shell command executed." if result["ok"] else "Shell command was blocked or failed.",
                )
        except Exception as exc:
            raise ComputerExecutionError(f"Failed to execute action {action.action_type}: {exc}") from exc

        raise ComputerExecutionError(f"Unsupported action type: {action.action_type}")

    def _validate_action(self, action: ComputerAction, safety_mode: SafetyMode) -> SafetyCheckResult:
        if action.action_type == ActionType.SHELL and not self.settings.allow_shell:
            return SafetyCheckResult(
                allowed=False,
                risk_level=RiskLevel.HIGH,
                reason="Shell execution is disabled in computer settings.",
            )

        if action.action_type in {
            ActionType.CLICK,
            ActionType.DOUBLE_CLICK,
            ActionType.RIGHT_CLICK,
        }:
            return self._validate_point(action.x, action.y)

        if action.action_type == ActionType.DRAG:
            start = self._validate_point(action.x, action.y)
            if not start.allowed:
                return start
            return self._validate_point(action.end_x, action.end_y)

        if action.action_type == ActionType.TYPE:
            text = str(action.text or "")
            return SafetyCheckResult(
                allowed=bool(text),
                risk_level=RiskLevel.LOW if text else RiskLevel.HIGH,
                reason="Typing requires non-empty text." if not text else "Typing text is low risk.",
            )

        if action.action_type == ActionType.PRESS:
            key = str(action.key or "").strip()
            return SafetyCheckResult(
                allowed=bool(key),
                risk_level=RiskLevel.LOW if key else RiskLevel.HIGH,
                reason="Press actions require a key." if not key else "Single-key press is low risk.",
            )

        if action.action_type == ActionType.HOTKEY:
            return SafetyCheckResult(
                allowed=len(action.keys) >= 2,
                risk_level=RiskLevel.MEDIUM if len(action.keys) >= 2 else RiskLevel.HIGH,
                reason=(
                    "Hotkeys need at least two keys."
                    if len(action.keys) < 2
                    else "Keyboard shortcut was explicitly requested."
                ),
            )

        if action.action_type == ActionType.SCROLL:
            return SafetyCheckResult(
                allowed=action.amount is not None,
                risk_level=RiskLevel.LOW,
                reason="Scroll is low risk.",
            )

        if action.action_type == ActionType.SHELL:
            return SafetyCheckResult.model_validate(
                validate_command(action.command or "", safety_mode=safety_mode.value).to_dict()
            )

        return SafetyCheckResult(
            allowed=True,
            risk_level=RiskLevel.LOW,
            reason="Observation does not mutate the computer.",
        )

    def _validate_point(self, x: int | None, y: int | None) -> SafetyCheckResult:
        if x is None or y is None:
            return SafetyCheckResult(
                allowed=False,
                risk_level=RiskLevel.HIGH,
                reason="Pointer actions require explicit coordinates.",
            )

        screen_size = vision.get_screen_size()
        width = int(screen_size["width"])
        height = int(screen_size["height"])
        if 0 <= int(x) < width and 0 <= int(y) < height:
            return SafetyCheckResult(
                allowed=True,
                risk_level=RiskLevel.LOW,
                reason="Coordinates are within the current screen bounds.",
            )

        return SafetyCheckResult(
            allowed=False,
            risk_level=RiskLevel.HIGH,
            reason=f"Coordinates ({x}, {y}) fall outside the screen bounds {width}x{height}.",
        )

    def _normalize_safety_mode(self, safety_mode: SafetyMode | str | None) -> SafetyMode:
        if isinstance(safety_mode, SafetyMode):
            return safety_mode
        if isinstance(safety_mode, str):
            try:
                return SafetyMode(safety_mode.lower())
            except ValueError:
                return SafetyMode.STRICT
        return SafetyMode(self.settings.safety_mode)
