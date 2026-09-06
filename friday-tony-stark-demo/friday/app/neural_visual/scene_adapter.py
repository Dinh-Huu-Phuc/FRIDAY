from __future__ import annotations

from typing import Any

from friday.app.neural_visual.schemas import NeuralTelemetryEvent
from friday.app.neural_visual.topology import NEURAL_EDGES, NEURAL_NODES, NeuralNodeId


NEURAL_SCENE_LAYERS = (
    {
        "id": "senses",
        "label": "INPUT / SENSES",
        "color": "#58e1e5",
        "x": -6.0,
    },
    {
        "id": "routing",
        "label": "INTENT / ROUTING",
        "color": "#70e6a7",
        "x": -3.0,
    },
    {
        "id": "knowledge",
        "label": "MEMORY / KNOWLEDGE",
        "color": "#6291ff",
        "x": 0.0,
    },
    {
        "id": "actions",
        "label": "TOOLS / ACTIONS",
        "color": "#f0b75e",
        "x": 3.0,
    },
    {
        "id": "response",
        "label": "RESPONSE / VOICE",
        "color": "#ff766e",
        "x": 6.0,
    },
)

_GROUP_TO_LAYER = {
    "INPUT": "senses",
    "PERCEPTION": "senses",
    "COGNITION": "routing",
    "MEMORY": "knowledge",
    "KNOWLEDGE": "knowledge",
    "REASONING": "knowledge",
    "TOOLS": "actions",
    "SYSTEM": "actions",
    "INTEGRATIONS": "actions",
    "OUTPUT": "response",
}

_BRAIN_POSITIONS = {
    NeuralNodeId.TEXT_INPUT: (-4.55, 1.75, 0.35),
    NeuralNodeId.MICROPHONE: (-4.75, -1.35, 0.90),
    NeuralNodeId.SPEECH_RECOGNITION: (-3.45, -2.30, -0.55),
    NeuralNodeId.SCREEN_VISION: (-3.85, 0.10, -1.55),
    NeuralNodeId.INTENT_ROUTER: (-2.40, 0.25, 0.55),
    NeuralNodeId.LIVE_SEARCH: (-0.90, 2.15, -1.10),
    NeuralNodeId.MEMORY: (-0.85, -2.05, 1.25),
    NeuralNodeId.LLM: (0.0, 0.0, 0.0),
    NeuralNodeId.POWER: (2.05, 2.35, 0.55),
    NeuralNodeId.CALENDAR: (3.65, 1.55, -0.85),
    NeuralNodeId.BROWSER: (2.35, 0.75, 1.65),
    NeuralNodeId.INTEGRATIONS: (2.75, -1.20, -1.45),
    NeuralNodeId.LOCAL_TOOLS: (2.15, -2.55, 0.60),
    NeuralNodeId.RESPONSE: (4.00, 0.0, 0.20),
    NeuralNodeId.UI: (5.05, 1.25, -0.70),
    NeuralNodeId.TTS: (5.00, -1.45, 0.85),
}


def _node_position(node) -> dict[str, float]:
    x, y, z = _BRAIN_POSITIONS[node.id]
    return {"x": x, "y": y, "z": z}


def build_neural_scene_payload() -> dict[str, Any]:
    layers = [dict(layer) for layer in NEURAL_SCENE_LAYERS]
    layer_map = {layer["id"]: layer for layer in layers}
    nodes = []
    for node in NEURAL_NODES:
        layer_id = _GROUP_TO_LAYER[node.group]
        nodes.append(
            {
                "id": node.id,
                "label": "FRIDAY / LLM" if node.id == NeuralNodeId.LLM else node.label,
                "description": node.description,
                "group": node.group,
                "layer": layer_id,
                "color": layer_map[layer_id]["color"],
                "position": _node_position(node),
                "radius": (
                    0.20
                    if node.id == NeuralNodeId.LLM
                    else 0.145
                    if node.core
                    else round(0.072 + node.radius * 0.005, 3)
                ),
                "core": bool(node.core),
            }
        )

    return {
        "version": 1,
        "layers": layers,
        "nodes": nodes,
        "edges": [
            {
                "id": edge.id,
                "source": edge.source,
                "target": edge.target,
                "bend": edge.bend,
            }
            for edge in NEURAL_EDGES
        ],
    }


def serialize_neural_event(event: NeuralTelemetryEvent) -> dict[str, Any]:
    return {
        "eventId": event.event_id,
        "traceId": event.trace_id,
        "sourceNode": event.source_node,
        "targetNode": event.target_node,
        "eventType": event.event_type,
        "summary": event.summary,
        "status": event.status.value,
        "durationMs": event.duration_ms,
        "createdAt": event.created_at,
    }
