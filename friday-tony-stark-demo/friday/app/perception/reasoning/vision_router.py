from __future__ import annotations

import asyncio
import json
import logging
import os
import threading
import time
from collections.abc import Callable
from dataclasses import replace
from typing import TYPE_CHECKING

from friday.app.perception.reasoning.gemma_vision import (
    GemmaVisionClient,
    VisionModelError,
    VisionModelTimeout,
)
from friday.app.perception.reasoning.question_policy import (
    QuestionKind,
    classify_camera_question,
    current_scene_context,
    historical_context,
    structured_answer,
)
from friday.app.perception.reasoning.schemas import (
    VisionReasoningResult,
    VisionReasoningStatus,
)
from friday.app.perception.reasoning.telemetry import OllamaTimings, VisionLatency
from friday.app.perception.scene.schemas import TemporalSceneSnapshot
from friday.app.perception.world import WorldSnapshot

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
        clock: Callable[[], float] = time.time,
    ) -> None:
        self._perception = perception_service
        self._clock = clock
        self._client = client or GemmaVisionClient()
        self._enabled = reasoning_enabled() if enabled is None else enabled
        self._cache_seconds = (
            _environment_float("FRIDAY_VISION_REASONING_CACHE_SECONDS", 3.0, 0.0, 30.0)
            if cache_seconds is None
            else max(0.0, cache_seconds)
        )
        self._inference_lock = threading.Lock()
        self._state_lock = threading.RLock()
        self._cached_key: tuple[int, str, str, str] | None = None
        self._cached_answer: VisionReasoningResult | None = None
        self._cached_at = 0.0
        self._last_result: VisionReasoningResult | None = None

    async def analyze(self, question: str) -> VisionReasoningResult:
        started = time.perf_counter()
        return await asyncio.to_thread(self.analyze_sync, question, _started_at=started)

    def analyze_sync(
        self, question: str, *, _started_at: float | None = None
    ) -> VisionReasoningResult:
        entered = time.perf_counter()
        started = entered if _started_at is None else _started_at
        stages: dict[str, float] = {
            "dispatch_wait_ms": max(0.0, entered - started) * 1000
        }
        policy = classify_camera_question(question)
        invoked = False
        provider_timings = OllamaTimings()

        def finish(result: VisionReasoningResult, route: str) -> VisionReasoningResult:
            timings = VisionLatency(
                route=route,
                question_kind=policy.kind.value,
                total_ms=(time.perf_counter() - started) * 1000,
                gemma_invoked=invoked,
                ollama=provider_timings,
                **stages,
            )
            result = replace(result, latency_ms=timings.total_ms, timings=timings)
            LOGGER.info("Vision latency: %s", json.dumps(timings.to_dict()))
            return self._remember(result)

        snapshot = self._perception.snapshot()
        getter = getattr(self._perception, "temporal_snapshot", None)
        temporal = getter() if callable(getter) else None
        if not isinstance(temporal, TemporalSceneSnapshot):
            temporal = None
        now = self._clock()
        scene_context = (
            current_scene_context(temporal, now=now)
            if temporal is not None and snapshot.status == "ready"
            else self._perception.describe_scene()[:800]
        )
        world_getter = getattr(self._perception, "world_snapshot", None)
        world = (
            world_getter()
            if (policy.operation == "holding" or policy.kind == QuestionKind.HISTORY)
            and callable(world_getter)
            else None
        )
        world_summary = ""
        if policy.kind == QuestionKind.HISTORY:
            world_summary = (
                historical_context(world, question, now=now)
                if isinstance(world, WorldSnapshot) and world.entities
                else self._perception.describe_world(question=question)[:2400]
            )
        fallback = scene_context + (f"\n\n{world_summary}" if world_summary else "")
        fast = (
            structured_answer(policy, temporal, now=now, world=world)
            if snapshot.status == "ready"
            else None
        )
        stages["context_build_ms"] = (time.perf_counter() - entered) * 1000
        if fast is not None:
            return finish(
                VisionReasoningResult(
                    status=VisionReasoningStatus.READY,
                    answer=fast.answer,
                    confidence=fast.confidence,
                    observations=fast.observations,
                    uncertainty=fast.uncertainty,
                ),
                "structured",
            )
        if snapshot.status != "ready":
            return finish(
                VisionReasoningResult(
                    status=(
                        VisionReasoningStatus.FALLBACK
                        if world_summary
                        else VisionReasoningStatus.UNAVAILABLE
                    ),
                    answer=fallback,
                    error=f"camera scene status is {snapshot.status}",
                ),
                "fallback",
            )
        if not self._enabled:
            return finish(
                VisionReasoningResult(
                    status=VisionReasoningStatus.FALLBACK,
                    answer=fallback,
                    error="camera reasoning is disabled",
                ),
                "fallback",
            )

        queued_at = time.perf_counter()
        acquired = self._inference_lock.acquire(blocking=False)
        stages["queue_wait_ms"] = (time.perf_counter() - queued_at) * 1000
        if not acquired:
            return finish(
                VisionReasoningResult(
                    status=VisionReasoningStatus.FALLBACK,
                    answer="I am still analyzing another camera request, Boss. Here is the structured evidence available now.\n\n"
                    + fallback,
                    error="camera reasoning is busy",
                ),
                "busy",
            )
        try:
            try:
                keyframe = self._perception.capture_keyframe(timings=stages)
            except (RuntimeError, ValueError) as exc:
                return finish(
                    VisionReasoningResult(
                        status=VisionReasoningStatus.FALLBACK,
                        answer="I could not prepare a camera image.\n\n" + fallback,
                        error=f"keyframe preparation failed ({type(exc).__name__})",
                    ),
                    "fallback",
                )
            if keyframe is None or not keyframe.jpeg_bytes:
                return finish(
                    VisionReasoningResult(
                        status=VisionReasoningStatus.FALLBACK
                        if world_summary
                        else VisionReasoningStatus.UNAVAILABLE,
                        answer=fallback,
                        error="no camera keyframe is available",
                    ),
                    "fallback",
                )
            keyframe = replace(
                keyframe, world_summary=world_summary, scene_summary=scene_context
            )
            cache_key = (
                keyframe.sequence,
                _normalize_question(question),
                world_summary,
                scene_context,
            )
            cached = self._cached_result(cache_key)
            if cached is not None:
                return finish(cached, "cache")
            started_at = time.perf_counter()
            invoked = True
            try:
                output = self._client.analyze(question, keyframe)
            except VisionModelError as exc:
                provider_timings = exc.timings
                stages["ollama_request_ms"] = (time.perf_counter() - started_at) * 1000
                LOGGER.warning("Camera reasoning fallback: %s", type(exc).__name__)
                explanation = (
                    "The local image analysis took too long, Boss."
                    if isinstance(exc, VisionModelTimeout)
                    else "I could not complete the local image analysis, Boss."
                )
                return finish(
                    VisionReasoningResult(
                        status=VisionReasoningStatus.FALLBACK,
                        answer=(
                            f"{explanation} I can only report detector observations "
                            "and remembered state, not reliably explain what is "
                            f"happening from the image yet.\n\n{fallback}"
                        ),
                        model=self._client.model,
                        keyframe_sequence=keyframe.sequence,
                        keyframe_reason=keyframe.reason,
                        latency_ms=(time.perf_counter() - started_at) * 1000,
                        error=str(exc),
                    ),
                    "fallback",
                )

            stages["ollama_request_ms"] = (time.perf_counter() - started_at) * 1000
            provider_timings = output.timings
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
                self._cached_answer = result
            return finish(result, "gemma")
        finally:
            self._inference_lock.release()

    def last_result(self) -> VisionReasoningResult | None:
        with self._state_lock:
            return self._last_result

    def _cached_result(
        self,
        cache_key: tuple[int, str, str, str],
    ) -> VisionReasoningResult | None:
        with self._state_lock:
            if (
                self._cached_key != cache_key
                or self._cached_answer is None
                or time.monotonic() - self._cached_at > self._cache_seconds
            ):
                return None
            return replace(self._cached_answer, used_cache=True)

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
