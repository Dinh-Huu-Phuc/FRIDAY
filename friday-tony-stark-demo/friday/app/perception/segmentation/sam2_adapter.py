from __future__ import annotations

import importlib.util
import threading
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Protocol

from friday.app.perception.detection.schemas import BoundingBox
from friday.app.perception.reasoning.schemas import VisionKeyframe
from friday.app.perception.segmentation.config import Sam2Config
from friday.app.perception.segmentation.schemas import SegmentationCapabilities


class Sam2ModelError(RuntimeError):
    """Raised when the optional local SAM 2 runtime cannot produce a mask."""


@dataclass(frozen=True, slots=True)
class Sam2Prediction:
    mask: Any
    confidence: float
    model: str
    device: str


class Sam2Backend(Protocol):
    model_name: str
    device: str

    def predict(self, jpeg_bytes: bytes, box: BoundingBox) -> Sam2Prediction: ...


BackendLoader = Callable[[Sam2Config], Sam2Backend]


class Sam2ImageSegmenter:
    """Lazily load the official SAM 2 image predictor for explicit requests."""

    def __init__(
        self,
        config: Sam2Config | None = None,
        *,
        backend_loader: BackendLoader | None = None,
    ) -> None:
        self.config = config or Sam2Config.from_environment()
        self._backend_loader = backend_loader or _load_official_backend
        self._backend: Sam2Backend | None = None
        self._load_lock = threading.Lock()
        self._inference_lock = threading.Lock()

    @property
    def model(self) -> str:
        return self._backend.model_name if self._backend else "sam2.1-hiera-tiny"

    @property
    def device(self) -> str:
        return self._backend.device if self._backend else self.config.device

    def capabilities(self) -> SegmentationCapabilities:
        package_available = importlib.util.find_spec("sam2") is not None
        checkpoint_available = self.config.checkpoint_path.is_file()
        return SegmentationCapabilities(
            enabled=self.config.enabled,
            package_available=package_available,
            checkpoint_available=checkpoint_available,
            checkpoint_path=str(self.config.checkpoint_path),
            sam2_model_config=self.config.model_config,
            requested_device=self.config.device,
            tracking_fps=self.config.tracking_fps,
            ready=self.config.enabled and package_available and checkpoint_available,
        )

    def segment(
        self,
        keyframe: VisionKeyframe,
        box: BoundingBox,
    ) -> Sam2Prediction:
        if not self.config.enabled:
            raise Sam2ModelError("SAM 2 segmentation is disabled.")
        if not keyframe.jpeg_bytes:
            raise Sam2ModelError("The selected camera keyframe is empty.")
        backend = self._ensure_backend()
        with self._inference_lock:
            try:
                return backend.predict(keyframe.jpeg_bytes, box)
            except Sam2ModelError:
                raise
            except Exception as exc:
                raise Sam2ModelError(f"SAM 2 inference failed: {exc}") from exc

    def unload(self) -> None:
        with self._load_lock:
            self._backend = None
        try:
            import torch

            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except (ImportError, RuntimeError):
            pass

    def _ensure_backend(self) -> Sam2Backend:
        if self._backend is not None:
            return self._backend
        with self._load_lock:
            if self._backend is None:
                self._backend = self._backend_loader(self.config)
        return self._backend


class _OfficialSam2Backend:
    def __init__(
        self,
        *,
        torch: Any,
        numpy: Any,
        cv2: Any,
        predictor: Any,
        model_name: str,
        device: str,
        multimask_output: bool,
    ) -> None:
        self._torch = torch
        self._numpy = numpy
        self._cv2 = cv2
        self._predictor = predictor
        self.model_name = model_name
        self.device = device
        self._multimask_output = multimask_output

    def predict(self, jpeg_bytes: bytes, box: BoundingBox) -> Sam2Prediction:
        encoded = self._numpy.frombuffer(jpeg_bytes, dtype=self._numpy.uint8)
        frame = self._cv2.imdecode(encoded, self._cv2.IMREAD_COLOR)
        if frame is None:
            raise Sam2ModelError("OpenCV could not decode the SAM 2 keyframe.")
        rgb = self._cv2.cvtColor(frame, self._cv2.COLOR_BGR2RGB)
        prompt_box = self._numpy.asarray(
            [box.x1, box.y1, box.x2, box.y2],
            dtype=self._numpy.float32,
        )
        try:
            with self._torch.inference_mode():
                self._predictor.set_image(rgb)
                masks, scores, _ = self._predictor.predict(
                    point_coords=None,
                    point_labels=None,
                    box=prompt_box,
                    multimask_output=self._multimask_output,
                )
        finally:
            reset = getattr(self._predictor, "reset_predictor", None)
            if callable(reset):
                reset()
        if masks is None or len(masks) == 0:
            raise Sam2ModelError("SAM 2 did not return a mask for the selected box.")
        score_values = self._numpy.asarray(scores, dtype=float).reshape(-1)
        best_index = int(score_values.argmax()) if len(score_values) else 0
        mask_values = self._numpy.asarray(masks)
        best_mask = mask_values[best_index] if mask_values.ndim >= 3 else mask_values
        confidence = float(score_values[best_index]) if len(score_values) else 0.0
        return Sam2Prediction(
            mask=best_mask > 0,
            confidence=min(1.0, max(0.0, confidence)),
            model=self.model_name,
            device=self.device,
        )


def _load_official_backend(config: Sam2Config) -> Sam2Backend:
    if not config.checkpoint_path.is_file():
        raise Sam2ModelError(
            "SAM 2 checkpoint is missing. Place sam2.1_hiera_tiny.pt at "
            f"{config.checkpoint_path} or set FRIDAY_SAM2_CHECKPOINT."
        )
    try:
        import cv2
        import numpy as np
        import torch
        from sam2.build_sam import build_sam2
        from sam2.sam2_image_predictor import SAM2ImagePredictor
    except ImportError as exc:
        raise Sam2ModelError(
            "SAM 2 needs Meta's optional local package. Install the official "
            "facebookresearch/sam2 package; Windows users should prefer WSL or "
            "build with SAM2_BUILD_CUDA=0."
        ) from exc

    device = _select_device(torch, config.device, config.minimum_cuda_vram_mb)
    try:
        model = build_sam2(
            config.model_config,
            str(config.checkpoint_path),
            device=device,
            apply_postprocessing=True,
        )
        predictor = SAM2ImagePredictor(model)
    except Exception as exc:
        raise Sam2ModelError(f"Could not load the SAM 2 model: {exc}") from exc
    return _OfficialSam2Backend(
        torch=torch,
        numpy=np,
        cv2=cv2,
        predictor=predictor,
        model_name="sam2.1-hiera-tiny",
        device=device,
        multimask_output=config.multimask_output,
    )


def _select_device(torch: Any, requested: str, minimum_cuda_vram_mb: int) -> str:
    normalized = requested if requested in {"auto", "cpu", "cuda"} else "auto"
    cuda_available = bool(torch.cuda.is_available())
    if normalized == "cpu":
        return "cpu"
    if normalized == "cuda":
        if not cuda_available:
            raise Sam2ModelError("CUDA was requested for SAM 2 but is unavailable.")
        return "cuda"
    if not cuda_available:
        return "cpu"
    try:
        total_mb = int(torch.cuda.get_device_properties(0).total_memory / (1024 * 1024))
    except (AttributeError, RuntimeError, TypeError, ValueError):
        return "cpu"
    return "cuda" if total_mb >= minimum_cuda_vram_mb else "cpu"
