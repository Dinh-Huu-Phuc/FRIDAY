from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import uuid4


class NeuralVisualAction(str, Enum):
    NONE = "none"
    OPEN = "open"
    CLOSE = "close"


class NeuralEventStatus(str, Enum):
    ACTIVE = "active"
    SUCCESS = "success"
    ERROR = "error"


@dataclass(frozen=True, slots=True)
class NeuralVisualIntentMatch:
    action: NeuralVisualAction = NeuralVisualAction.NONE
    trigger_id: str = ""


@dataclass(frozen=True, slots=True)
class NeuralVisualCommandResult:
    handled: bool
    accepted: bool = False
    action: NeuralVisualAction = NeuralVisualAction.NONE
    message: str = ""


@dataclass(frozen=True, slots=True)
class NeuralTelemetryEvent:
    trace_id: str
    target_node: str
    event_type: str
    summary: str
    status: NeuralEventStatus = NeuralEventStatus.ACTIVE
    source_node: str | None = None
    duration_ms: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    event_id: str = field(default_factory=lambda: uuid4().hex)
    created_at: str = field(
        default_factory=lambda: datetime.now(UTC).isoformat(timespec="milliseconds")
    )
