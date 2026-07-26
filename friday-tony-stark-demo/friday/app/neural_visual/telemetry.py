from __future__ import annotations

from collections import deque
from collections.abc import Callable
from threading import RLock
from typing import Any
from uuid import uuid4

from friday.app.neural_visual.event_sanitizer import sanitize_neural_summary
from friday.app.neural_visual.schemas import NeuralEventStatus, NeuralTelemetryEvent
from friday.app.neural_visual.topology import NEURAL_EDGE_MAP, NEURAL_NODE_MAP

NeuralTelemetrySubscriber = Callable[[NeuralTelemetryEvent], None]


class NeuralTelemetryBus:
    def __init__(self, *, history_size: int = 200) -> None:
        self._lock = RLock()
        self._subscribers: list[NeuralTelemetrySubscriber] = []
        self._history: deque[NeuralTelemetryEvent] = deque(maxlen=history_size)

    def subscribe(self, subscriber: NeuralTelemetrySubscriber) -> Callable[[], None]:
        with self._lock:
            if subscriber not in self._subscribers:
                self._subscribers.append(subscriber)

        def unsubscribe() -> None:
            with self._lock:
                if subscriber in self._subscribers:
                    self._subscribers.remove(subscriber)

        return unsubscribe

    def publish(self, event: NeuralTelemetryEvent) -> bool:
        if event.target_node not in NEURAL_NODE_MAP:
            return False
        if event.source_node is not None:
            edge_id = f"{event.source_node}->{event.target_node}"
            if edge_id not in NEURAL_EDGE_MAP:
                return False
        with self._lock:
            self._history.append(event)
            subscribers = tuple(self._subscribers)
        for subscriber in subscribers:
            try:
                subscriber(event)
            except RuntimeError:
                continue
        return True

    def recent_events(self) -> tuple[NeuralTelemetryEvent, ...]:
        with self._lock:
            return tuple(self._history)

    def clear(self) -> None:
        with self._lock:
            self._history.clear()


_TELEMETRY_BUS = NeuralTelemetryBus()


def get_neural_telemetry_bus() -> NeuralTelemetryBus:
    return _TELEMETRY_BUS


def new_neural_trace_id() -> str:
    return uuid4().hex


def emit_neural_activity(
    node_id: str,
    *,
    trace_id: str | None = None,
    event_type: str,
    summary: Any = "",
    status: NeuralEventStatus = NeuralEventStatus.ACTIVE,
    duration_ms: float | None = None,
    metadata: dict[str, Any] | None = None,
) -> str:
    resolved_trace_id = trace_id or new_neural_trace_id()
    get_neural_telemetry_bus().publish(
        NeuralTelemetryEvent(
            trace_id=resolved_trace_id,
            target_node=node_id,
            event_type=event_type,
            summary=sanitize_neural_summary(summary),
            status=status,
            duration_ms=duration_ms,
            metadata=dict(metadata or {}),
        )
    )
    return resolved_trace_id


def emit_neural_transfer(
    source_node: str,
    target_node: str,
    *,
    trace_id: str,
    event_type: str,
    summary: Any = "",
    status: NeuralEventStatus = NeuralEventStatus.ACTIVE,
    duration_ms: float | None = None,
    metadata: dict[str, Any] | None = None,
) -> bool:
    return get_neural_telemetry_bus().publish(
        NeuralTelemetryEvent(
            trace_id=trace_id,
            source_node=source_node,
            target_node=target_node,
            event_type=event_type,
            summary=sanitize_neural_summary(summary),
            status=status,
            duration_ms=duration_ms,
            metadata=dict(metadata or {}),
        )
    )
