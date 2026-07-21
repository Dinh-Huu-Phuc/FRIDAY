"""Route-style entrypoints for computer control."""

from friday.app.computer.dependencies import get_computer_service
from friday.app.computer.schemas.requests import ExecuteRequest, ObserveRequest, PlanRequest, RunRequest
from friday.app.computer.schemas.responses import ExecuteResponse, ObserveResponse, PlanResponse, RunResponse
from friday.app.computer.service.service import ComputerService


def observe_computer(
    request: ObserveRequest | None = None,
    service: ComputerService | None = None,
) -> ObserveResponse:
    active_service = service or get_computer_service()
    return active_service.observe(request)


def plan_computer(
    request: PlanRequest,
    service: ComputerService | None = None,
) -> PlanResponse:
    active_service = service or get_computer_service()
    return active_service.plan_next_action(request)


def execute_computer_action(
    request: ExecuteRequest,
    service: ComputerService | None = None,
) -> ExecuteResponse:
    active_service = service or get_computer_service()
    return active_service.execute_action(request)


def run_computer_cycle(
    request: RunRequest,
    service: ComputerService | None = None,
) -> RunResponse:
    active_service = service or get_computer_service()
    return active_service.run_single_cycle(request)
