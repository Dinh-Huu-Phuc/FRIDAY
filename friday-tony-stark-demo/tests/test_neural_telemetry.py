from __future__ import annotations

from friday.app.neural_visual.event_sanitizer import sanitize_neural_summary
from friday.app.neural_visual.schemas import (
    NeuralEventStatus,
    NeuralTelemetryEvent,
)
from friday.app.neural_visual.telemetry import NeuralTelemetryBus
from friday.app.neural_visual.topology import (
    NEURAL_EDGE_MAP,
    NEURAL_NODE_MAP,
    NeuralNodeId,
)


def test_neural_topology_uses_stable_semantic_ids() -> None:
    assert NeuralNodeId.INTENT_ROUTER in NEURAL_NODE_MAP
    assert NeuralNodeId.LLM in NEURAL_NODE_MAP
    assert NeuralNodeId.CALENDAR in NEURAL_NODE_MAP
    assert (
        f"{NeuralNodeId.SPEECH_RECOGNITION}->{NeuralNodeId.INTENT_ROUTER}"
        in NEURAL_EDGE_MAP
    )
    assert (
        f"{NeuralNodeId.RESPONSE}->{NeuralNodeId.TTS}"
        in NEURAL_EDGE_MAP
    )
    assert (
        f"{NeuralNodeId.CALENDAR}->{NeuralNodeId.RESPONSE}"
        in NEURAL_EDGE_MAP
    )


def test_neural_telemetry_bus_dispatches_real_transfers_and_unsubscribes() -> None:
    bus = NeuralTelemetryBus()
    received: list[NeuralTelemetryEvent] = []
    unsubscribe = bus.subscribe(received.append)
    event = NeuralTelemetryEvent(
        trace_id="trace-1",
        source_node=NeuralNodeId.TEXT_INPUT,
        target_node=NeuralNodeId.INTENT_ROUTER,
        event_type="intent.routing.started",
        summary="Search the latest robotics news",
    )

    assert bus.publish(event)
    assert bus.recent_events() == (event,)
    unsubscribe()
    assert bus.publish(
        NeuralTelemetryEvent(
            trace_id="trace-1",
            source_node=NeuralNodeId.INTENT_ROUTER,
            target_node=NeuralNodeId.LIVE_SEARCH,
            event_type="search.web.started",
            summary="robotics news",
        )
    )
    assert received == [event]


def test_neural_telemetry_rejects_unknown_nodes_and_edges() -> None:
    bus = NeuralTelemetryBus()

    assert not bus.publish(
        NeuralTelemetryEvent(
            trace_id="trace-invalid",
            target_node="unknown.node",
            event_type="invalid",
            summary="ignored",
        )
    )
    assert not bus.publish(
        NeuralTelemetryEvent(
            trace_id="trace-invalid-edge",
            source_node=NeuralNodeId.MICROPHONE,
            target_node=NeuralNodeId.LLM,
            event_type="invalid",
            summary="ignored",
        )
    )


def test_neural_summary_redacts_credentials_and_limits_size() -> None:
    summary = sanitize_neural_summary(
        "password=hunter2 token:abc123 "
        "postgresql://friday:secret-value@database.local/postgres "
        + "x" * 300
    )

    assert "hunter2" not in summary
    assert "abc123" not in summary
    assert "secret-value" not in summary
    assert "[REDACTED]" in summary
    assert len(summary) <= 150


def test_neural_event_keeps_trace_status_and_latency() -> None:
    event = NeuralTelemetryEvent(
        trace_id="trace-latency",
        source_node=NeuralNodeId.LLM,
        target_node=NeuralNodeId.RESPONSE,
        event_type="llm.response.completed",
        summary="Answer ready",
        status=NeuralEventStatus.SUCCESS,
        duration_ms=412.5,
    )

    assert event.trace_id == "trace-latency"
    assert event.status is NeuralEventStatus.SUCCESS
    assert event.duration_ms == 412.5
