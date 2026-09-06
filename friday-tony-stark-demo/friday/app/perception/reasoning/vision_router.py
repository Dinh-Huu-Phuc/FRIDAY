from __future__ import annotations

import asyncio
import logging
import os
import threading
import time
from dataclasses import replace
from typing import TYPE_CHECKING

from friday.app.perception.reasoning.gemma_vision import (
    GemmaVisionClient,
    VisionModelError,
)
from friday.app.perception.reasoning.schemas import (
    VisionReasoningResult,
    VisionReasoningStatus,
)

if TYPE_CHECKING:
    from friday.app.perception.service import PerceptionService

LOGGER = logging.getLogger(__name__)


class VisionRouter:
    """Route explicit camera questions to one serialized local VLM request."""

    def __init__(
        self,
        perception_service: PerceptionService,
        *,
        client: GemmaVisionClient | None = None,
        enabled: bool | None = None,
        cache_seconds: float | None = None,
    ) -> None:
        self._perception = perception_service
        self._client = client or GemmaVisionClient()
        self._enabled = reasoning_enabled() if enabled is None else enabled
        self._cache_seconds = (
            _environment_float(
                "FRIDAY_VISION_REASONING_CACHE_SECONDS", 3.0, 0.0, 30.0
            )
            if cache_seconds is None
            else max(0.0, cache_seconds)
        )
        self._inference_lock = threading.Lock()
        self._state_lock = threading.RLock()
        self._cached_key: tuple[int, str] | None = None
        self._cached_at = 0.0
        self._last_result: VisionReasoningResult | None = None

    async def analyze(self, question: str) -> VisionReasoningResult:
        return await asyncio.to_thread(self.analyze_sync, question)

    def analyze_sync(self, question: str) -> VisionReasoningResult:
        fallback = self._perception.describe_scene()
        snapshot = self._perception.snapshot()
        if snapshot.status != "ready":
            return self._remember(
                VisionReasoningResult(
                    status=VisionReasoningStatus.UNAVAILABLE,
                    answer=fallback,
                    error=f"camera scene status is {snapshot.status}",
                )
            )
        if not self._enabled:
            return self._remember(
                VisionReasoningResult(
                    status=VisionReasoningStatus.FALLBACK,
                    answer=fallback,
                    error="camera reasoning is disabled",
                )
            )

        keyframe = self._perception.capture_keyframe()
        if keyframe is None or not keyframe.jpeg_bytes:
            return self._remember(
                VisionReasoningResult(
                    status=VisionReasoningStatus.UNAVAILABLE,
                    answer=fallback,
                    error="no camera keyframe is available",
                )
            )

        cache_key = (keyframe.sequence, _normalize_question(question))
        cached = self._cached_result(cache_key)
        if cached is not None:
            return cached

        with self._inference_lock:
            cached = self._cached_result(cache_key)
            if cached is not None:
                return cached
            started_at = time.perf_counter()
            try:
                output = self._client.analyze(question, keyframe)
            except VisionModelError as exc:
                LOGGER.warning("Camera reasoning fell back to scene state: %s", exc)
                return self._remember(
                    VisionReasoningResult(
                        status=VisionReasoningStatus.FALLBACK,
                        answer=fallback,
                        model=self._client.model,
                        keyframe_sequence=keyframe.sequence,
                        keyframe_reason=keyframe.reason,
                        latency_ms=(time.perf_counter() - started_at) * 1000,
                        error=str(exc),
                    )
                )

            result = VisionReasoningResult(
                status=VisionReasoningStatus.READY,
                answer=output.answer,
                model=self._client.model,
                keyframe_sequence=keyframe.sequence,
                keyframe_reason=keyframe.reason,
                latency_ms=(time.perf_counter() - started_at) * 1000,
                confidence=output.confidence,
                observations=output.observations,
                uncertainty=output.uncertainty,
            )
            with self._state_lock:
                self._cached_key = cache_key
                self._cached_at = time.monotonic()
            return self._remember(result)

    def last_result(self) -> VisionReasoningResult | None:
        with self._state_lock:
            return self._last_result

    def _cached_result(
        self,
        cache_key: tuple[int, str],
    ) -> VisionReasoningResult | None:
        with self._state_lock:
            if (
                self._cached_key != cache_key
                or self._last_result is None
                or self._last_result.status != VisionReasoningStatus.READY
                or time.monotonic() - self._cached_at > self._cache_seconds
            ):
                return None
            return replace(self._last_result, used_cache=True)

    def _remember(self, result: VisionReasoningResult) -> VisionReasoningResult:
        with self._state_lock:
            self._last_result = result
        return result


def reasoning_enabled() -> bool:
    return (os.getenv("FRIDAY_VISION_REASONING_ENABLED") or "true").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def _normalize_question(question: str) -> str:
    return " ".join(str(question or "").lower().split())


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


_ROUTER_LOCK = threading.Lock()
_VISION_ROUTER: VisionRouter | None = None


def get_vision_router() -> VisionRouter:
    global _VISION_ROUTER
    with _ROUTER_LOCK:
        if _VISION_ROUTER is None:
            from friday.app.perception.service import get_perception_service

            _VISION_ROUTER = VisionRouter(get_perception_service())
        return _VISION_ROUTER


async def analyze_camera_scene(question: str) -> VisionReasoningResult:
    return await get_vision_router().analyze(question)
