from __future__ import annotations

from friday.app.neural_visual.scene_adapter import (
    build_neural_scene_payload,
    serialize_neural_event,
)
from friday.app.neural_visual.schemas import NeuralEventStatus, NeuralTelemetryEvent
from friday.app.neural_visual.topology import NEURAL_EDGES, NEURAL_NODES, NeuralNodeId


def test_scene_payload_maps_every_runtime_node_into_five_stable_3d_layers() -> None:
    payload = build_neural_scene_payload()

    assert [layer["id"] for layer in payload["layers"]] == [
        "senses",
        "routing",
        "knowledge",
        "actions",
        "response",
    ]
    assert len(payload["nodes"]) == len(NEURAL_NODES)
    assert len(payload["edges"]) == len(NEURAL_EDGES)
    assert {node["id"] for node in payload["nodes"]} == {
        node.id for node in NEURAL_NODES
    }
    assert all(
        set(node["position"]) == {"x", "y", "z"}
        for node in payload["nodes"]
    )
    assert len({
        tuple(node["position"].values())
        for node in payload["nodes"]
    }) == len(NEURAL_NODES)

    llm = next(node for node in payload["nodes"] if node["id"] == NeuralNodeId.LLM)
    assert llm["position"] == {"x": 0.0, "y": 0.0, "z": 0.0}
    assert llm["label"] == "FRIDAY / LLM"


def test_scene_edges_reference_existing_nodes() -> None:
    payload = build_neural_scene_payload()
    node_ids = {node["id"] for node in payload["nodes"]}

    assert all(
        edge["source"] in node_ids and edge["target"] in node_ids
        for edge in payload["edges"]
    )


def test_scene_event_serializer_keeps_trace_direction_status_and_latency() -> None:
    event = NeuralTelemetryEvent(
        trace_id="trace-3d",
        source_node=NeuralNodeId.TEXT_INPUT,
        target_node=NeuralNodeId.INTENT_ROUTER,
        event_type="intent.routing.started",
        summary="Route a desktop command",
        status=NeuralEventStatus.SUCCESS,
        duration_ms=18.5,
        metadata={"secret": "must-not-cross-the-ui-boundary"},
    )

    payload = serialize_neural_event(event)

    assert payload["traceId"] == "trace-3d"
    assert payload["sourceNode"] == NeuralNodeId.TEXT_INPUT
    assert payload["targetNode"] == NeuralNodeId.INTENT_ROUTER
    assert payload["status"] == "success"
    assert payload["durationMs"] == 18.5
    assert "metadata" not in payload
    assert "secret" not in str(payload)
