"""High-level orchestration service for the computer module."""

from __future__ import annotations

from friday.app.computer.config.settings import ComputerSettings
from friday.app.computer.schemas.entities import ComputerAction, RuntimeContextSnapshot, SafetyMode, ScreenObservation
from friday.app.computer.schemas.requests import ExecuteRequest, ObserveRequest, PlanRequest, RunRequest
from friday.app.computer.schemas.responses import ExecuteResponse, ObserveResponse, PlanResponse, RunResponse
from friday.app.computer.service.executor import ComputerExecutor
from friday.app.computer.service.observer import ComputerObserver
from friday.app.computer.service.planner import ComputerPlanner
from friday.runtime_context import get_computer_runtime_context, update_computer_runtime_context


class ComputerService:
    def __init__(
        self,
        *,
        settings: ComputerSettings,
        observer: ComputerObserver,
        planner: ComputerPlanner,
        executor: ComputerExecutor,
    ) -> None:
        self.settings = settings
        self.observer = observer
        self.planner = planner
        self.executor = executor

    def observe(self, request: ObserveRequest | None = None) -> ObserveResponse:
        active_request = request or ObserveRequest()
        observation = self.observer.observe(active_request)
        runtime_context = update_computer_runtime_context(
            active_window_title=observation.active_window_title,
            last_screenshot_path=observation.screenshot_path,
            screen_width=observation.screen_width,
            screen_height=observation.screen_height,
            current_goal=active_request.goal or get_computer_runtime_context().get("current_goal", ""),
        )
        return ObserveResponse(
            observation=observation,
            runtime_context=self._runtime_snapshot(runtime_context),
            message="Screen observation captured.",
        )

    def plan_next_action(self, request: PlanRequest) -> PlanResponse:
        observation = request.observation
        if observation is None:
            observation = self.observe(ObserveRequest(goal=request.goal)).observation

        runtime_context = request.runtime_context or self._runtime_snapshot(get_computer_runtime_context())
        action, reasoning = self.planner.plan_next_action(
            goal=request.goal,
            observation=observation,
            runtime_context=runtime_context,
        )
        updated_runtime = update_computer_runtime_context(
            current_goal=request.goal,
            current_plan=[action.description or action.action_type],
        )
        return PlanResponse(
            goal=request.goal,
            action=action,
            reasoning=reasoning,
            runtime_context=self._runtime_snapshot(updated_runtime),
            message="Planned one next action.",
        )

    def execute_action(self, request: ExecuteRequest) -> ExecuteResponse:
        runtime_before = self._runtime_snapshot(get_computer_runtime_context())
        safety_mode = request.safety_mode or runtime_before.safety_mode or SafetyMode(self.settings.safety_mode)
        safety, executed, result, message = self.executor.execute_action(
            request.action,
            safety_mode=safety_mode,
        )
        updated_runtime = update_computer_runtime_context(
            last_action=request.action.model_dump(by_alias=True, mode="json"),
            safety_mode=safety_mode.value if hasattr(safety_mode, "value") else str(safety_mode),
        )
        ok = executed if request.action.action_type != "observe" else safety.allowed
        return ExecuteResponse(
            ok=ok,
            action=request.action,
            executed=executed,
            safety=safety,
            result=result,
            runtime_context=self._runtime_snapshot(updated_runtime),
            message=message,
        )

    def run_single_cycle(self, request: RunRequest) -> RunResponse:
        safety_mode = request.safety_mode or SafetyMode(self.settings.safety_mode)
        update_computer_runtime_context(
            current_goal=request.goal,
            safety_mode=safety_mode.value if hasattr(safety_mode, "value") else str(safety_mode),
        )

        observation = request.observation
        if observation is None:
            observation = self.observe(ObserveRequest(goal=request.goal)).observation

        plan_response = self.plan_next_action(
            PlanRequest(
                goal=request.goal,
                observation=observation,
                runtime_context=self._runtime_snapshot(get_computer_runtime_context()),
            )
        )
        execution_response = self.execute_action(
            ExecuteRequest(
                action=plan_response.action,
                safety_mode=safety_mode,
            )
        )
        runtime_context = self._runtime_snapshot(get_computer_runtime_context())
        return RunResponse(
            ok=plan_response.ok and execution_response.safety.allowed,
            goal=request.goal,
            observation=observation,
            action=plan_response.action,
            planning_reasoning=plan_response.reasoning,
            execution=execution_response,
            runtime_context=runtime_context,
            message="Completed one computer control cycle.",
        )

    def _runtime_snapshot(self, payload: dict[str, object]) -> RuntimeContextSnapshot:
        return RuntimeContextSnapshot.model_validate(payload)
