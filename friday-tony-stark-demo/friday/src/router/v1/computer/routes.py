from __future__ import annotations

from fastapi import APIRouter

from friday.app.computer.schemas.requests import ExecuteRequest, ObserveRequest, PlanRequest, RunRequest
from friday.src.services.computer.service import execute, observe, plan, run


router = APIRouter()


@router.post("/observe")
def observe_route(payload: ObserveRequest):
    return observe(payload)


@router.post("/plan")
def plan_route(payload: PlanRequest):
    return plan(payload)


@router.post("/execute")
def execute_route(payload: ExecuteRequest):
    return execute(payload)


@router.post("/run")
def run_route(payload: RunRequest):
    return run(payload)
