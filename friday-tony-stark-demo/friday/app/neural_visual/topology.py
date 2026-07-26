from __future__ import annotations

from dataclasses import dataclass


class NeuralNodeId:
    MICROPHONE = "input.microphone"
    TEXT_INPUT = "input.text"
    SPEECH_RECOGNITION = "perception.stt"
    INTENT_ROUTER = "cognition.intent"
    MEMORY = "memory.context"
    LIVE_SEARCH = "knowledge.live_search"
    SCREEN_VISION = "perception.vision"
    BROWSER = "automation.browser"
    INTEGRATIONS = "integrations.messaging"
    POWER = "system.power"
    LOCAL_TOOLS = "tools.local"
    LLM = "reasoning.llm"
    RESPONSE = "response.composer"
    UI = "output.ui"
    TTS = "output.tts"


@dataclass(frozen=True, slots=True)
class NeuralNodeDefinition:
    id: str
    label: str
    description: str
    group: str
    x: float
    y: float
    radius: float = 4.2
    core: bool = False


@dataclass(frozen=True, slots=True)
class NeuralEdgeDefinition:
    source: str
    target: str
    bend: float = 0.0

    @property
    def id(self) -> str:
        return f"{self.source}->{self.target}"


NEURAL_NODES = (
    NeuralNodeDefinition(
        NeuralNodeId.TEXT_INPUT,
        "TEXT",
        "Typed commands and questions from the operator.",
        "INPUT",
        0.06,
        0.25,
    ),
    NeuralNodeDefinition(
        NeuralNodeId.MICROPHONE,
        "MIC",
        "Live microphone audio captured by the desktop console.",
        "INPUT",
        0.06,
        0.76,
    ),
    NeuralNodeDefinition(
        NeuralNodeId.SPEECH_RECOGNITION,
        "STT",
        "Converts captured speech into a refined transcript.",
        "PERCEPTION",
        0.20,
        0.76,
    ),
    NeuralNodeDefinition(
        NeuralNodeId.INTENT_ROUTER,
        "INTENT",
        "Classifies the request and selects the responsible subsystem.",
        "COGNITION",
        0.32,
        0.50,
        radius=6.2,
        core=True,
    ),
    NeuralNodeDefinition(
        NeuralNodeId.POWER,
        "POWER",
        "Handles sleep, wake and local window state.",
        "SYSTEM",
        0.49,
        0.10,
    ),
    NeuralNodeDefinition(
        NeuralNodeId.BROWSER,
        "BROWSER",
        "Controls Chrome, websites and platform searches.",
        "TOOLS",
        0.49,
        0.25,
    ),
    NeuralNodeDefinition(
        NeuralNodeId.LIVE_SEARCH,
        "SEARCH",
        "Retrieves current public information and source context.",
        "KNOWLEDGE",
        0.49,
        0.40,
    ),
    NeuralNodeDefinition(
        NeuralNodeId.SCREEN_VISION,
        "VISION",
        "Captures and understands the active computer display.",
        "PERCEPTION",
        0.49,
        0.55,
    ),
    NeuralNodeDefinition(
        NeuralNodeId.INTEGRATIONS,
        "COMMS",
        "Reads approved messaging, mail and integration data.",
        "INTEGRATIONS",
        0.49,
        0.70,
    ),
    NeuralNodeDefinition(
        NeuralNodeId.LOCAL_TOOLS,
        "TOOLS",
        "Runs local workspace, Code Map and desktop commands.",
        "TOOLS",
        0.49,
        0.84,
    ),
    NeuralNodeDefinition(
        NeuralNodeId.MEMORY,
        "MEMORY",
        "Builds conversation, workspace and retrieval context.",
        "MEMORY",
        0.66,
        0.82,
    ),
    NeuralNodeDefinition(
        NeuralNodeId.LLM,
        "OLLAMA / LLM",
        "Reasons over prepared context and generates an answer.",
        "REASONING",
        0.67,
        0.45,
        radius=6.8,
        core=True,
    ),
    NeuralNodeDefinition(
        NeuralNodeId.RESPONSE,
        "RESPONSE",
        "Normalizes the final answer for display and speech.",
        "OUTPUT",
        0.81,
        0.50,
        radius=5.5,
    ),
    NeuralNodeDefinition(
        NeuralNodeId.UI,
        "DISPLAY",
        "Renders the answer in the active FRIDAY interface.",
        "OUTPUT",
        0.94,
        0.31,
    ),
    NeuralNodeDefinition(
        NeuralNodeId.TTS,
        "VOICE",
        "Synthesizes and plays FRIDAY's spoken response.",
        "OUTPUT",
        0.94,
        0.68,
    ),
)


def _edge(source: str, target: str, bend: float = 0.0) -> NeuralEdgeDefinition:
    return NeuralEdgeDefinition(source=source, target=target, bend=bend)


NEURAL_EDGES = (
    _edge(NeuralNodeId.MICROPHONE, NeuralNodeId.SPEECH_RECOGNITION),
    _edge(NeuralNodeId.SPEECH_RECOGNITION, NeuralNodeId.INTENT_ROUTER, 0.03),
    _edge(NeuralNodeId.TEXT_INPUT, NeuralNodeId.INTENT_ROUTER, -0.03),
    _edge(NeuralNodeId.INTENT_ROUTER, NeuralNodeId.POWER, -0.08),
    _edge(NeuralNodeId.INTENT_ROUTER, NeuralNodeId.BROWSER, -0.05),
    _edge(NeuralNodeId.INTENT_ROUTER, NeuralNodeId.LIVE_SEARCH, -0.02),
    _edge(NeuralNodeId.INTENT_ROUTER, NeuralNodeId.SCREEN_VISION, 0.02),
    _edge(NeuralNodeId.INTENT_ROUTER, NeuralNodeId.INTEGRATIONS, 0.05),
    _edge(NeuralNodeId.INTENT_ROUTER, NeuralNodeId.LOCAL_TOOLS, 0.08),
    _edge(NeuralNodeId.INTENT_ROUTER, NeuralNodeId.MEMORY, 0.08),
    _edge(NeuralNodeId.MEMORY, NeuralNodeId.LIVE_SEARCH, -0.10),
    _edge(NeuralNodeId.MEMORY, NeuralNodeId.LLM, 0.04),
    _edge(NeuralNodeId.LIVE_SEARCH, NeuralNodeId.LLM, -0.04),
    _edge(NeuralNodeId.POWER, NeuralNodeId.RESPONSE, -0.08),
    _edge(NeuralNodeId.BROWSER, NeuralNodeId.RESPONSE, -0.05),
    _edge(NeuralNodeId.LIVE_SEARCH, NeuralNodeId.RESPONSE, -0.02),
    _edge(NeuralNodeId.SCREEN_VISION, NeuralNodeId.RESPONSE, 0.02),
    _edge(NeuralNodeId.INTEGRATIONS, NeuralNodeId.RESPONSE, 0.05),
    _edge(NeuralNodeId.LOCAL_TOOLS, NeuralNodeId.RESPONSE, 0.08),
    _edge(NeuralNodeId.MEMORY, NeuralNodeId.RESPONSE, 0.10),
    _edge(NeuralNodeId.LLM, NeuralNodeId.RESPONSE),
    _edge(NeuralNodeId.RESPONSE, NeuralNodeId.UI, -0.04),
    _edge(NeuralNodeId.RESPONSE, NeuralNodeId.TTS, 0.04),
)

NEURAL_NODE_MAP = {node.id: node for node in NEURAL_NODES}
NEURAL_EDGE_MAP = {edge.id: edge for edge in NEURAL_EDGES}

