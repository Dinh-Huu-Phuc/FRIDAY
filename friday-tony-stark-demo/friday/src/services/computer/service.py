from __future__ import annotations

from friday.app.computer.router.routes import execute_computer_action, observe_computer, plan_computer, run_computer_cycle
from friday.app.computer.schemas.requests import ExecuteRequest, ObserveRequest, PlanRequest, RunRequest


def observe(payload: ObserveRequest):
    return observe_computer(payload)


def plan(payload: PlanRequest):
    return plan_computer(payload)


def execute(payload: ExecuteRequest):
    return execute_computer_action(payload)


def run(payload: RunRequest):
    return run_computer_cycle(payload)
