"""Response models for the computer module."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from friday.app.computer.schemas.entities import ComputerAction, RuntimeContextSnapshot, SafetyCheckResult, ScreenObservation


class ObserveResponse(BaseModel):
    ok: bool = True
    observation: ScreenObservation
    runtime_context: RuntimeContextSnapshot
    message: str


class PlanResponse(BaseModel):
    ok: bool = True
    goal: str
    action: ComputerAction
    reasoning: str
    runtime_context: RuntimeContextSnapshot
    message: str


class ExecuteResponse(BaseModel):
    ok: bool
    action: ComputerAction
    executed: bool
    safety: SafetyCheckResult
    result: dict[str, Any] = Field(default_factory=dict)
    runtime_context: RuntimeContextSnapshot
    message: str


class RunResponse(BaseModel):
    ok: bool
    goal: str
    observation: ScreenObservation
    action: ComputerAction
    planning_reasoning: str
    execution: ExecuteResponse
    runtime_context: RuntimeContextSnapshot
    message: str
