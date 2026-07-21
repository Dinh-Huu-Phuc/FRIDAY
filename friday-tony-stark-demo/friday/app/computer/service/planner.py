"""Single-step planner for the computer module."""

from __future__ import annotations

import re

from friday.app.computer.constants import DEFAULT_SCROLL_AMOUNT
from friday.app.computer.config.settings import ComputerSettings
from friday.app.computer.schemas.entities import ActionType, ComputerAction, RuntimeContextSnapshot, ScreenObservation
from friday.prompts import get_computer_agent_constitution, get_computer_agent_system_prompt


POINT_PATTERN = re.compile(r"(?P<x>\d{1,5})\s*[,x]\s*(?P<y>\d{1,5})")
DRAG_PATTERN = re.compile(
    r"(?:from|tu)\s*(?P<x1>\d{1,5})\s*[,x]\s*(?P<y1>\d{1,5}).*?(?:to|den)\s*(?P<x2>\d{1,5})\s*[,x]\s*(?P<y2>\d{1,5})",
    re.IGNORECASE,
)
KEY_ALIASES = {
    "control": "ctrl",
    "return": "enter",
    "windows": "win",
    "command": "win",
    "escape": "esc",
}
PRESS_KEYWORDS = ("press ", "nhan phim ", "bam phim ")
TYPE_KEYWORDS = ("type ", "go ", "nhap ")
SHELL_KEYWORDS = ("shell", "terminal", "powershell", "cmd", "command")


class ComputerPlanner:
    def __init__(self, *, settings: ComputerSettings) -> None:
        self.settings = settings

    def plan_next_action(
        self,
        *,
        goal: str,
        observation: ScreenObservation | None,
        runtime_context: RuntimeContextSnapshot | None,
    ) -> tuple[ComputerAction, str]:
        goal_text = str(goal or "").strip()
        context = runtime_context or RuntimeContextSnapshot(safety_mode=self.settings.safety_mode)
        window_title = ""
        if observation is not None:
            window_title = observation.active_window_title
        if not window_title:
            window_title = context.active_window_title

        _ = self._build_internal_prompt(goal_text, observation, context)
        action = self._plan_from_goal(goal_text, observation, context)
        reasoning = (
            f"Planned exactly one step for '{window_title or 'unknown window'}': "
            f"{action.description or action.action_type}."
        )
        return action, reasoning

    def _build_internal_prompt(
        self,
        goal: str,
        observation: ScreenObservation | None,
        runtime_context: RuntimeContextSnapshot,
    ) -> str:
        observation_text = "no observation available"
        if observation is not None:
            observation_text = (
                f"path={observation.screenshot_path}, "
                f"window={observation.active_window_title}, "
                f"size={observation.screen_width}x{observation.screen_height}"
            )
        return (
            f"{get_computer_agent_system_prompt()}\n\n"
            f"{get_computer_agent_constitution()}\n\n"
            f"goal={goal}\n"
            f"observation={observation_text}\n"
            f"runtime_goal={runtime_context.current_goal}\n"
            f"safety_mode={runtime_context.safety_mode}"
        )

    def _plan_from_goal(
        self,
        goal: str,
        observation: ScreenObservation | None,
        runtime_context: RuntimeContextSnapshot,
    ) -> ComputerAction:
        lowered = goal.lower()
        if not goal.strip():
            return self._observe_action("No goal was provided.")
        if observation is None:
            return self._observe_action("No fresh observation is available yet.")

        drag_match = DRAG_PATTERN.search(lowered)
        if drag_match:
            return ComputerAction(
                type=ActionType.DRAG,
                description="Drag from the start point to the end point.",
                x=int(drag_match.group("x1")),
                y=int(drag_match.group("y1")),
                end_x=int(drag_match.group("x2")),
                end_y=int(drag_match.group("y2")),
                rationale="The goal includes explicit drag coordinates.",
            )

        shell_command = self._extract_shell_command(goal)
        if shell_command:
            return ComputerAction(
                type=ActionType.SHELL,
                description="Run one validated shell command.",
                command=shell_command,
                timeout=self.settings.default_command_timeout,
                rationale="The goal explicitly requested terminal execution.",
            )

        hotkey_keys = self._extract_hotkey(lowered)
        if hotkey_keys:
            return ComputerAction(
                type=ActionType.HOTKEY,
                description="Press one keyboard shortcut.",
                keys=hotkey_keys,
                rationale="The goal includes an explicit hotkey combination.",
            )

        typed_text = self._extract_quoted_text(goal)
        if typed_text and any(keyword in lowered for keyword in TYPE_KEYWORDS):
            return ComputerAction(
                type=ActionType.TYPE,
                description="Type the requested text.",
                text=typed_text,
                rationale="The goal includes quoted input text.",
            )

        pressed_key = self._extract_pressed_key(lowered)
        if pressed_key:
            return ComputerAction(
                type=ActionType.PRESS,
                description="Press one keyboard key.",
                key=pressed_key,
                rationale="The goal includes a single key press.",
            )

        scroll_amount = self._extract_scroll_amount(lowered)
        if scroll_amount is not None:
            return ComputerAction(
                type=ActionType.SCROLL,
                description="Scroll a small amount.",
                amount=scroll_amount,
                rationale="The goal explicitly requested scrolling.",
            )

        point = self._extract_point(goal, observation)
        if "double click" in lowered or "double-click" in lowered:
            if point is None:
                return self._observe_action("Double click was requested without a clear point.")
            return ComputerAction(
                type=ActionType.DOUBLE_CLICK,
                description="Double click the requested point.",
                x=point[0],
                y=point[1],
                rationale="The goal explicitly requested a double click.",
            )

        if "right click" in lowered or "right-click" in lowered:
            if point is None:
                return self._observe_action("Right click was requested without a clear point.")
            return ComputerAction(
                type=ActionType.RIGHT_CLICK,
                description="Right click the requested point.",
                x=point[0],
                y=point[1],
                rationale="The goal explicitly requested a right click.",
            )

        if any(keyword in lowered for keyword in ("click", "bam", "nhan vao")):
            if point is None:
                return self._observe_action("Click was requested without coordinates.")
            return ComputerAction(
                type=ActionType.CLICK,
                description="Click the requested point.",
                x=point[0],
                y=point[1],
                rationale="The goal explicitly requested a click.",
            )

        return self._observe_action(
            "The goal is underspecified, so the safest next step is to observe again."
        )

    def _observe_action(self, reason: str) -> ComputerAction:
        return ComputerAction(
            type=ActionType.OBSERVE,
            description="Observe the current screen before acting.",
            rationale=reason,
        )

    def _extract_point(
        self,
        goal: str,
        observation: ScreenObservation,
    ) -> tuple[int, int] | None:
        match = POINT_PATTERN.search(goal)
        if match:
            return int(match.group("x")), int(match.group("y"))

        lowered = goal.lower()
        if "center" in lowered or "giua man hinh" in lowered:
            return observation.screen_width // 2, observation.screen_height // 2
        return None

    def _extract_quoted_text(self, goal: str) -> str | None:
        for pattern in (r'"([^"]+)"', r"'([^']+)'"):
            match = re.search(pattern, goal)
            if match:
                return match.group(1).strip()
        return None

    def _extract_hotkey(self, lowered_goal: str) -> list[str]:
        hotkey_match = re.search(
            r"((?:ctrl|control|alt|shift|win|windows|command)(?:\s*\+\s*[a-z0-9]+)+)",
            lowered_goal,
        )
        if not hotkey_match:
            return []

        parts = [part.strip() for part in hotkey_match.group(1).split("+") if part.strip()]
        normalized = [KEY_ALIASES.get(part, part) for part in parts]
        return normalized if len(normalized) >= 2 else []

    def _extract_pressed_key(self, lowered_goal: str) -> str | None:
        for keyword in PRESS_KEYWORDS:
            if keyword not in lowered_goal:
                continue
            tail = lowered_goal.split(keyword, maxsplit=1)[1].strip()
            if not tail:
                return None
            key = tail.split()[0].strip(",. ")
            return KEY_ALIASES.get(key, key)
        return None

    def _extract_scroll_amount(self, lowered_goal: str) -> int | None:
        if "scroll" not in lowered_goal and "cuon" not in lowered_goal:
            return None

        amount_match = re.search(r"(\d+)", lowered_goal)
        amount = int(amount_match.group(1)) if amount_match else DEFAULT_SCROLL_AMOUNT
        if "down" in lowered_goal or "xuong" in lowered_goal:
            return -abs(amount)
        return abs(amount)

    def _extract_shell_command(self, goal: str) -> str | None:
        lowered = goal.lower()
        if not any(keyword in lowered for keyword in SHELL_KEYWORDS):
            return None

        quoted = self._extract_quoted_text(goal)
        if quoted:
            return quoted

        for keyword in SHELL_KEYWORDS:
            if keyword not in lowered:
                continue
            index = lowered.index(keyword) + len(keyword)
            command = goal[index:].strip(" :.-")
            if command:
                return command
        return None
