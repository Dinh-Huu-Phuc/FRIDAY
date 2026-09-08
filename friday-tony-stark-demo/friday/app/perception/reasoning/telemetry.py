from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class OllamaTimings:
    total_duration_ms: float | None = None
    load_duration_ms: float | None = None
    prompt_eval_duration_ms: float | None = None
    eval_duration_ms: float | None = None
    prompt_eval_count: int | None = None
    eval_count: int | None = None

    @classmethod
    def from_response(cls, response: dict[str, Any]) -> OllamaTimings:
        values = {}
        for name in (
            "total_duration",
            "load_duration",
            "prompt_eval_duration",
            "eval_duration",
        ):
            value = response.get(name)
            if (
                isinstance(value, (int, float))
                and not isinstance(value, bool)
                and math.isfinite(value)
                and value >= 0
            ):
                values[f"{name}_ms"] = value / 1_000_000
        for name in ("prompt_eval_count", "eval_count"):
            value = response.get(name)
            if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
                values[name] = value
        return cls(**values)


@dataclass(frozen=True, slots=True)
class VisionLatency:
    route: str
    question_kind: str
    total_ms: float
    gemma_invoked: bool = False
    frame_acquisition_ms: float = 0.0
    jpeg_encoding_ms: float = 0.0
    context_build_ms: float = 0.0
    queue_wait_ms: float = 0.0
    dispatch_wait_ms: float = 0.0
    ollama_request_ms: float = 0.0
    ollama: OllamaTimings = field(default_factory=OllamaTimings)

    def to_dict(self) -> dict:
        """Numbers and routing labels only: never frames, prompts, or answers."""
        return asdict(self)
