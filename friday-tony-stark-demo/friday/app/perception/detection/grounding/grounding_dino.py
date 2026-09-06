from __future__ import annotations

import io
import os
import threading
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Protocol

from friday.app.perception.detection.grounding.schemas import GroundingMatch
from friday.app.perception.detection.schemas import BoundingBox
from friday.app.perception.reasoning.schemas import VisionKeyframe


class GroundingModelError(RuntimeError):
    """Raised when the optional local open-vocabulary detector is unavailable."""


class GroundingBackend(Protocol):
    model_name: str
    device: str

    def detect(
        self,
        jpeg_bytes: bytes,
        queries: tuple[str, ...],
        *,
        box_threshold: float,
        text_threshold: float,
        max_results: int,
    ) -> tuple[GroundingMatch, ...]: ...


BackendLoader = Callable[[str, str, bool, int], GroundingBackend]


@dataclass(frozen=True, slots=True)
class GroundingDinoConfig:
    model_id: str
    device: str
    local_files_only: bool
    minimum_cuda_vram_mb: int
    box_threshold: float
    text_threshold: float
    max_results: int

    @classmethod
    def from_environment(cls) -> GroundingDinoConfig:
        return cls(
            model_id=(
                os.getenv("FRIDAY_GROUNDING_MODEL")
                or "IDEA-Research/grounding-dino-tiny"
            ).strip(),
            device=(os.getenv("FRIDAY_GROUNDING_DEVICE") or "auto").strip().lower(),
            local_files_only=_environment_bool(
                "FRIDAY_GROUNDING_LOCAL_FILES_ONLY", False
            ),
            minimum_cuda_vram_mb=_environment_int(
                "FRIDAY_GROUNDING_MIN_CUDA_VRAM_MB", 6144, 1024, 65536
            ),
            box_threshold=_environment_float(
                "FRIDAY_GROUNDING_BOX_THRESHOLD", 0.35, 0.05, 0.95
            ),
            text_threshold=_environment_float(
                "FRIDAY_GROUNDING_TEXT_THRESHOLD", 0.25, 0.05, 0.95
            ),
            max_results=_environment_int("FRIDAY_GROUNDING_MAX_RESULTS", 5, 1, 20),
        )


class GroundingDinoDetector:
    """Lazily load Grounding DINO and run it only for explicit text queries."""

    def __init__(
        self,
        config: GroundingDinoConfig | None = None,
        *,
        backend_loader: BackendLoader | None = None,
    ) -> None:
        self.config = config or GroundingDinoConfig.from_environment()
        self._backend_loader = backend_loader or _load_transformers_backend
        self._backend: GroundingBackend | None = None
        self._load_lock = threading.Lock()

    @property
    def model(self) -> str:
        return self.config.model_id

    @property
    def device(self) -> str:
        return self._backend.device if self._backend is not None else self.config.device

    def detect(
        self,
        keyframe: VisionKeyframe,
        query: str,
    ) -> tuple[GroundingMatch, ...]:
        return self.detect_many(keyframe, (query,))

    def detect_many(
        self,
        keyframe: VisionKeyframe,
        queries: tuple[str, ...],
        *,
        max_results: int | None = None,
    ) -> tuple[GroundingMatch, ...]:
        if not keyframe.jpeg_bytes:
            raise GroundingModelError("The selected camera keyframe is empty.")
        normalized_queries = tuple(
            cleaned
            for query in queries
            if (cleaned := " ".join(str(query or "").strip().split()))
        )
        if not normalized_queries:
            raise GroundingModelError("At least one object label is required.")
        backend = self._ensure_backend()
        try:
            return backend.detect(
                keyframe.jpeg_bytes,
                normalized_queries,
                box_threshold=self.config.box_threshold,
                text_threshold=self.config.text_threshold,
                max_results=(
                    self.config.max_results
                    if max_results is None
                    else max(1, min(200, int(max_results)))
                ),
            )
        except GroundingModelError:
            raise
        except Exception as exc:
            raise GroundingModelError(
                f"Grounding DINO inference failed: {exc}"
            ) from exc

    def _ensure_backend(self) -> GroundingBackend:
        if self._backend is not None:
            return self._backend
        with self._load_lock:
            if self._backend is None:
                self._backend = self._backend_loader(
                    self.config.model_id,
                    self.config.device,
                    self.config.local_files_only,
                    self.config.minimum_cuda_vram_mb,
                )
        return self._backend


class _TransformersGroundingBackend:
    def __init__(
        self,
        *,
        torch: Any,
        image_type: Any,
        processor: Any,
        model: Any,
        model_name: str,
        device: str,
    ) -> None:
        self._torch = torch
        self._image_type = image_type
        self._processor = processor
        self._model = model
        self.model_name = model_name
        self.device = device

    def detect(
        self,
        jpeg_bytes: bytes,
        queries: tuple[str, ...],
        *,
        box_threshold: float,
        text_threshold: float,
        max_results: int,
    ) -> tuple[GroundingMatch, ...]:
        try:
            image = self._image_type.open(io.BytesIO(jpeg_bytes)).convert("RGB")
            inputs = self._processor(
                images=image,
                text=[list(queries)],
                return_tensors="pt",
            ).to(self.device)
            with self._torch.inference_mode():
                outputs = self._model(**inputs)
            results = self._processor.post_process_grounded_object_detection(
                outputs,
                inputs["input_ids"],
                threshold=box_threshold,
                text_threshold=text_threshold,
                target_sizes=[image.size[::-1]],
            )
        except Exception as exc:
            raise GroundingModelError(
                f"Could not process the camera keyframe: {exc}"
            ) from exc
        if not results:
            return ()
        result = results[0]
        labels = result.get("text_labels") or result.get("labels", ())
        fallback_label = queries[0]
        matches: list[GroundingMatch] = []
        for box, score, label in zip(
            result.get("boxes", ()),
            result.get("scores", ()),
            labels,
            strict=False,
        ):
            coordinates = _tensor_values(box)
            if len(coordinates) < 4:
                continue
            confidence = _scalar_value(score)
            matches.append(
                GroundingMatch(
                    label=str(label or fallback_label).strip(),
                    confidence=max(0.0, min(1.0, confidence)),
                    box=BoundingBox(
                        x1=max(0, round(coordinates[0])),
                        y1=max(0, round(coordinates[1])),
                        x2=max(0, round(coordinates[2])),
                        y2=max(0, round(coordinates[3])),
                    ),
                )
            )
        matches.sort(key=lambda item: item.confidence, reverse=True)
        return tuple(matches[:max_results])


def _load_transformers_backend(
    model_id: str,
    requested_device: str,
    local_files_only: bool,
    minimum_cuda_vram_mb: int,
) -> GroundingBackend:
    try:
        import torch
        from PIL import Image
        from transformers import AutoModelForZeroShotObjectDetection, AutoProcessor
    except ImportError as exc:
        raise GroundingModelError(
            "Grounding DINO needs the optional vision-grounding dependencies. "
            "Run: uv sync --extra vision-grounding"
        ) from exc

    device = _select_device(torch, requested_device, minimum_cuda_vram_mb)
    try:
        processor = AutoProcessor.from_pretrained(
            model_id,
            local_files_only=local_files_only,
            trust_remote_code=False,
        )
        model = AutoModelForZeroShotObjectDetection.from_pretrained(
            model_id,
            local_files_only=local_files_only,
            trust_remote_code=False,
        )
        model.to(device)
        model.eval()
    except Exception as exc:
        mode = "local cache" if local_files_only else "Hugging Face model cache"
        raise GroundingModelError(
            f"Could not load {model_id} from the {mode}: {exc}"
        ) from exc
    return _TransformersGroundingBackend(
        torch=torch,
        image_type=Image,
        processor=processor,
        model=model,
        model_name=model_id,
        device=device,
    )


def _select_device(torch: Any, requested: str, minimum_cuda_vram_mb: int) -> str:
    normalized = requested if requested in {"auto", "cpu", "cuda"} else "auto"
    cuda_available = bool(torch.cuda.is_available())
    if normalized == "cpu":
        return "cpu"
    if normalized == "cuda":
        if not cuda_available:
            raise GroundingModelError(
                "CUDA was requested for Grounding DINO but is unavailable."
            )
        return "cuda"
    if not cuda_available:
        return "cpu"
    try:
        total_mb = int(torch.cuda.get_device_properties(0).total_memory / (1024 * 1024))
    except (AttributeError, RuntimeError, TypeError, ValueError):
        return "cpu"
    return "cuda" if total_mb >= minimum_cuda_vram_mb else "cpu"


def _tensor_values(value: Any) -> list[float]:
    if hasattr(value, "detach"):
        value = value.detach()
    if hasattr(value, "cpu"):
        value = value.cpu()
    if hasattr(value, "tolist"):
        value = value.tolist()
    return [float(item) for item in value]


def _scalar_value(value: Any) -> float:
    if hasattr(value, "item"):
        value = value.item()
    return float(value)


def _environment_bool(name: str, default: bool) -> bool:
    raw = (os.getenv(name) or ("true" if default else "false")).strip().lower()
    return raw in {"1", "true", "yes", "on"}


def _environment_float(
    name: str, default: float, minimum: float, maximum: float
) -> float:
    try:
        value = float((os.getenv(name) or str(default)).strip())
    except ValueError:
        return default
    return min(maximum, max(minimum, value))


def _environment_int(name: str, default: int, minimum: int, maximum: int) -> int:
    try:
        value = int((os.getenv(name) or str(default)).strip())
    except ValueError:
        return default
    return min(maximum, max(minimum, value))
