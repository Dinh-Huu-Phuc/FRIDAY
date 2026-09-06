from __future__ import annotations

import asyncio
import os
import threading
import time
from dataclasses import replace
from typing import TYPE_CHECKING

from friday.app.perception.detection.grounding.grounding_dino import (
    GroundingDinoDetector,
    GroundingModelError,
)
from friday.app.perception.detection.grounding.schemas import (
    GroundingMatch,
    GroundingResult,
    GroundingStatus,
)
from friday.app.perception.detection.schemas import BoundingBox

if TYPE_CHECKING:
    from friday.app.perception.service import PerceptionService


class OpenVocabularyService:
    """Locate text-described objects without adding load to the live detector."""

    def __init__(
        self,
        perception_service: PerceptionService,
        *,
        detector: GroundingDinoDetector | None = None,
        enabled: bool | None = None,
        cache_seconds: float | None = None,
    ) -> None:
        self._perception = perception_service
        self._detector = detector or GroundingDinoDetector()
        self._enabled = grounding_enabled() if enabled is None else enabled
        self._cache_seconds = (
            _environment_float("FRIDAY_GROUNDING_CACHE_SECONDS", 12.0, 0.0, 120.0)
            if cache_seconds is None
            else max(0.0, cache_seconds)
        )
        self._inference_lock = threading.Lock()
        self._state_lock = threading.RLock()
        self._cached_key: tuple[int, str] | None = None
        self._cached_at = 0.0
        self._last_result: GroundingResult | None = None

    async def locate(self, query: str) -> GroundingResult:
        return await asyncio.to_thread(self.locate_sync, query)

    def locate_sync(self, query: str) -> GroundingResult:
        cleaned_query = " ".join(str(query or "").strip().split())[:150]
        snapshot = self._perception.snapshot()
        if not cleaned_query:
            return self._remember(
                GroundingResult(
                    status=GroundingStatus.ERROR,
                    query="",
                    answer="Tell me which object to locate, Boss.",
                    error="empty grounding query",
                )
            )
        if snapshot.status != "ready":
            return self._remember(
                GroundingResult(
                    status=GroundingStatus.UNAVAILABLE,
                    query=cleaned_query,
                    answer="Open the Camera Window first so I can locate that object, Boss.",
                    error=f"camera scene status is {snapshot.status}",
                )
            )

        primary = _find_primary_matches(cleaned_query, snapshot.objects)
        if primary:
            result = _build_result(
                query=cleaned_query,
                matches=primary,
                model=snapshot.model_name,
                provider="primary_detector",
                device="onnx",
                keyframe_sequence=snapshot.sequence,
                frame_width=snapshot.frame_width,
                frame_height=snapshot.frame_height,
                latency_ms=0.0,
            )
            self._publish(result)
            return result

        if not self._enabled:
            return self._remember(
                GroundingResult(
                    status=GroundingStatus.UNAVAILABLE,
                    query=cleaned_query,
                    answer="Open-vocabulary camera search is disabled, Boss.",
                    error="Grounding DINO is disabled",
                )
            )

        keyframe = self._perception.capture_keyframe()
        if keyframe is None or not keyframe.jpeg_bytes:
            return self._remember(
                GroundingResult(
                    status=GroundingStatus.UNAVAILABLE,
                    query=cleaned_query,
                    answer="I could not capture a camera frame to search, Boss.",
                    error="no camera keyframe is available",
                )
            )
        cache_key = (keyframe.sequence, cleaned_query.casefold())
        cached = self._cached_result(cache_key)
        if cached is not None:
            self._publish(cached)
            return cached

        with self._inference_lock:
            cached = self._cached_result(cache_key)
            if cached is not None:
                self._publish(cached)
                return cached
            started_at = time.perf_counter()
            try:
                matches = self._detector.detect(keyframe, cleaned_query)
            except GroundingModelError as exc:
                result = GroundingResult(
                    status=GroundingStatus.UNAVAILABLE,
                    query=cleaned_query,
                    answer=(
                        "I could not start the local object finder. "
                        "The Grounding DINO component needs attention, Boss."
                    ),
                    model=self._detector.model,
                    device=self._detector.device,
                    keyframe_sequence=keyframe.sequence,
                    frame_width=keyframe.frame_width,
                    frame_height=keyframe.frame_height,
                    latency_ms=(time.perf_counter() - started_at) * 1000,
                    completed_at=time.monotonic(),
                    error=str(exc),
                )
                self._publish(result)
                return result

            result = _build_result(
                query=cleaned_query,
                matches=matches,
                model=self._detector.model,
                provider="grounding_dino",
                device=self._detector.device,
                keyframe_sequence=keyframe.sequence,
                frame_width=keyframe.frame_width,
                frame_height=keyframe.frame_height,
                latency_ms=(time.perf_counter() - started_at) * 1000,
            )
            with self._state_lock:
                self._cached_key = cache_key
                self._cached_at = time.monotonic()
            self._publish(result)
            return result

    def last_result(self) -> GroundingResult | None:
        with self._state_lock:
            return self._last_result

    def _cached_result(self, cache_key: tuple[int, str]) -> GroundingResult | None:
        with self._state_lock:
            if (
                self._cached_key != cache_key
                or self._last_result is None
                or not self._last_result.ok
                or time.monotonic() - self._cached_at > self._cache_seconds
            ):
                return None
            return replace(
                self._last_result,
                completed_at=time.monotonic(),
                used_cache=True,
            )

    def _publish(self, result: GroundingResult) -> None:
        self._remember(result)
        publisher = getattr(self._perception, "set_grounding_result", None)
        if callable(publisher):
            publisher(result)

    def _remember(self, result: GroundingResult) -> GroundingResult:
        with self._state_lock:
            self._last_result = result
        return result


def _find_primary_matches(query: str, objects: tuple) -> tuple[GroundingMatch, ...]:
    normalized = query.casefold().strip()
    words = normalized.split()
    if len(words) > 2:
        return ()
    singular = normalized.removesuffix("s")
    matches = (
        GroundingMatch(
            label=item.label,
            confidence=item.confidence,
            box=item.box,
        )
        for item in objects
        if item.label.casefold() in {normalized, singular}
    )
    return tuple(sorted(matches, key=lambda item: item.confidence, reverse=True))


def _build_result(
    *,
    query: str,
    matches: tuple[GroundingMatch, ...],
    model: str,
    provider: str,
    device: str,
    keyframe_sequence: int,
    frame_width: int,
    frame_height: int,
    latency_ms: float,
) -> GroundingResult:
    status = GroundingStatus.READY if matches else GroundingStatus.NOT_FOUND
    return GroundingResult(
        status=status,
        query=query,
        answer=_format_answer(query, matches, frame_width, frame_height),
        matches=matches,
        model=model,
        provider=provider,
        device=device,
        keyframe_sequence=keyframe_sequence,
        frame_width=frame_width,
        frame_height=frame_height,
        latency_ms=latency_ms,
        completed_at=time.monotonic(),
    )


def _format_answer(
    query: str,
    matches: tuple[GroundingMatch, ...],
    frame_width: int,
    frame_height: int,
) -> str:
    if not matches:
        return f"I could not locate {query} in the current camera view, Boss."
    best = matches[0]
    location = _describe_location(best.box, frame_width, frame_height)
    count = len(matches)
    count_text = "one match" if count == 1 else f"{count} matches"
    return (
        f"I found {count_text} for {query}. The strongest match is {location} "
        f"with {best.confidence:.0%} confidence, Boss."
    )


def _describe_location(box: BoundingBox, width: int, height: int) -> str:
    if width <= 0 or height <= 0:
        return "inside the camera view"
    center_x, center_y = box.center
    horizontal = "left" if center_x < width / 3 else "right" if center_x > width * 2 / 3 else "center"
    vertical = "upper" if center_y < height / 3 else "lower" if center_y > height * 2 / 3 else "middle"
    return f"in the {vertical}-{horizontal} area of the camera view"


def grounding_enabled() -> bool:
    return (os.getenv("FRIDAY_GROUNDING_ENABLED") or "true").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def grounding_result_ttl() -> float:
    return _environment_float("FRIDAY_GROUNDING_RESULT_TTL", 10.0, 1.0, 60.0)


def _environment_float(name: str, default: float, minimum: float, maximum: float) -> float:
    try:
        value = float((os.getenv(name) or str(default)).strip())
    except ValueError:
        return default
    return min(maximum, max(minimum, value))


_SERVICE_LOCK = threading.Lock()
_OPEN_VOCABULARY_SERVICE: OpenVocabularyService | None = None


def get_open_vocabulary_service() -> OpenVocabularyService:
    global _OPEN_VOCABULARY_SERVICE
    with _SERVICE_LOCK:
        if _OPEN_VOCABULARY_SERVICE is None:
            from friday.app.perception.service import get_perception_service

            _OPEN_VOCABULARY_SERVICE = OpenVocabularyService(get_perception_service())
        return _OPEN_VOCABULARY_SERVICE


async def locate_camera_object(query: str) -> GroundingResult:
    return await get_open_vocabulary_service().locate(query)
