from __future__ import annotations

import base64
import os
from collections.abc import Callable
from typing import Any

import httpx
from pydantic import BaseModel, Field, ValidationError

from friday.app.perception.reasoning.schemas import GemmaVisionOutput, VisionKeyframe
from friday.app.perception.reasoning.telemetry import OllamaTimings

JsonRequester = Callable[[str, dict[str, Any], float], dict[str, Any]]


class VisionModelError(RuntimeError):
    """Raised when the local camera reasoning provider cannot answer."""

    def __init__(self, message: str, *, timings: OllamaTimings | None = None) -> None:
        super().__init__(message)
        self.timings = timings or OllamaTimings()


class VisionModelTimeout(VisionModelError):
    """The provider did not finish camera analysis within its time limit."""


class _StructuredVisionAnswer(BaseModel):
    answer: str = Field(min_length=1, max_length=2400)
    observations: list[str] = Field(default_factory=list, max_length=8)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    uncertainty: str = Field(default="", max_length=800)


class GemmaVisionClient:
    def __init__(
        self,
        *,
        model: str | None = None,
        base_url: str | None = None,
        timeout_seconds: float | None = None,
        requester: JsonRequester | None = None,
    ) -> None:
        self.model = (model or os.getenv("FRIDAY_VISION_MODEL") or "gemma3:4b").strip()
        configured_url = (
            base_url or os.getenv("FRIDAY_VISION_BASE_URL") or "http://127.0.0.1:11434"
        ).rstrip("/")
        if configured_url not in {
            "http://127.0.0.1:11434",
            "http://localhost:11434",
        }:
            raise ValueError("FRIDAY_VISION_BASE_URL must point to local Ollama")
        self.endpoint = f"{configured_url}/api/chat"
        self.timeout_seconds = timeout_seconds or _environment_float(
            "FRIDAY_VISION_REASONING_TIMEOUT", 120.0, 10.0, 600.0
        )
        self.keep_alive = vision_keep_alive()
        self.num_predict = _environment_int(
            "FRIDAY_VISION_REASONING_NUM_PREDICT", 128, 64, 512
        )
        self.context_tokens = _environment_int(
            "FRIDAY_VISION_REASONING_CONTEXT", 2048, 1024, 8192
        )
        self._requester = requester or _post_json

    def analyze(
        self,
        question: str,
        keyframe: VisionKeyframe,
    ) -> GemmaVisionOutput:
        payload = {
            "model": self.model,
            "stream": False,
            "format": _StructuredVisionAnswer.model_json_schema(),
            "keep_alive": self.keep_alive,
            "options": {
                "temperature": 0.1,
                "num_ctx": self.context_tokens,
                "num_predict": self.num_predict,
            },
            "messages": [
                {
                    "role": "user",
                    "content": _build_prompt(question, keyframe),
                    "images": [base64.b64encode(keyframe.jpeg_bytes).decode("ascii")],
                }
            ],
        }
        try:
            result = self._requester(self.endpoint, payload, self.timeout_seconds)
        except (httpx.TimeoutException, TimeoutError) as exc:
            raise VisionModelTimeout(
                f"Local camera analysis timed out after {self.timeout_seconds:g} seconds"
            ) from exc
        except Exception as exc:  # Provider boundary: normalize transport failures.
            raise VisionModelError(
                f"Local Ollama request failed ({type(exc).__name__})"
            ) from exc
        timings = OllamaTimings.from_response(result)
        message = result.get("message")
        if not isinstance(message, dict) or not isinstance(message.get("content"), str):
            raise VisionModelError("Gemma returned an invalid message", timings=timings)
        content = message["content"].strip()
        if not content:
            raise VisionModelError(
                "Gemma returned an empty camera analysis", timings=timings
            )
        try:
            parsed = _parse_structured_answer(content)
        except VisionModelError as exc:
            exc.timings = timings
            raise
        if not parsed.answer.strip():
            raise VisionModelError(
                "Gemma returned a blank camera answer", timings=timings
            )
        return GemmaVisionOutput(
            answer=parsed.answer.strip(),
            observations=tuple(
                item.strip() for item in parsed.observations if item.strip()
            ),
            confidence=parsed.confidence,
            uncertainty=parsed.uncertainty.strip(),
            timings=timings,
        )


def _build_prompt(question: str, keyframe: VisionKeyframe) -> str:
    return (
        "You are FRIDAY's local camera scene-reasoning module. Answer in concise, "
        "natural English. Use the camera frame for current visible evidence. The detector "
        "context below is auxiliary and may be imperfect; never claim an object solely "
        "because the detector listed it. Do not identify a person's identity or infer "
        "sensitive personal traits. Distinguish visible facts from uncertainty. For "
        "questions about changes, use the event context but do not invent an earlier "
        "state. The world context records earlier observations, not proof of current "
        "visibility. For last-known-location questions use that history, state when "
        "the object was last seen, and say when it is absent or visibility is unknown. "
        "Positions are image-relative; do not invent a desk, room, owner, or person "
        "identity. If several entities share a label, explain the ambiguity. "
        "Return compact JSON with a one- or two-sentence answer, at most two short "
        "observations, confidence, and brief uncertainty. Avoid repeating detector IDs.\n\n"
        f"Keyframe reason: {keyframe.reason.value}.\n"
        f"Tracked scene context: {keyframe.scene_summary}\n"
        f"Session world context: {keyframe.world_summary[:2400] or 'No remembered world evidence.'}\n"
        f"User question: {question.strip()}"
    )


def _parse_structured_answer(content: str) -> _StructuredVisionAnswer:
    candidate = content.strip()
    if candidate.startswith("```"):
        candidate = candidate.removeprefix("```json").removeprefix("```")
        candidate = candidate.removesuffix("```").strip()
    try:
        return _StructuredVisionAnswer.model_validate_json(candidate)
    except ValidationError:
        if candidate.startswith(("{", "[")):
            raise VisionModelError(
                "Gemma returned incomplete or invalid structured JSON"
            ) from None
        return _StructuredVisionAnswer(
            answer=content.strip(),
            confidence=0.5,
            uncertainty="The model did not return structured confidence metadata.",
        )


def vision_keep_alive() -> str:
    """Shared by startup preload and all runtime camera requests."""
    return (os.getenv("FRIDAY_VISION_REASONING_KEEP_ALIVE") or "").strip() or "30m"


def preload_vision_model() -> None:
    """Startup-only warmup with the same model/context/retention as questions."""
    try:
        client = GemmaVisionClient()
        _post_json(
            client.endpoint.removesuffix("/chat") + "/generate",
            {
                "model": client.model,
                "prompt": "",
                "stream": False,
                "keep_alive": client.keep_alive,
                "options": {"num_ctx": client.context_tokens},
            },
            client.timeout_seconds,
        )
    except (httpx.HTTPError, ValueError, VisionModelError):
        # Startup is optional; normal requests retain their explicit fallback.
        return


def _post_json(
    endpoint: str,
    payload: dict[str, Any],
    timeout_seconds: float,
) -> dict[str, Any]:
    with httpx.Client(timeout=timeout_seconds) as client:
        response = client.post(endpoint, json=payload)
        response.raise_for_status()
        result = response.json()
    if not isinstance(result, dict):
        raise VisionModelError("Ollama returned an invalid response payload")
    return result


def _environment_float(
    name: str,
    default: float,
    minimum: float,
    maximum: float,
) -> float:
    try:
        value = float((os.getenv(name) or str(default)).strip())
    except ValueError:
        return default
    return min(maximum, max(minimum, value))


def _environment_int(
    name: str,
    default: int,
    minimum: int,
    maximum: int,
) -> int:
    try:
        value = int((os.getenv(name) or str(default)).strip())
    except ValueError:
        return default
    return min(maximum, max(minimum, value))
