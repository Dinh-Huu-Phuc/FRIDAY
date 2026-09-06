from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from friday.app.perception.detection.onnx_detector import (
    DetectionModelError,
    OnnxObjectDetector,
)
from friday.app.perception.evaluation.config import DetectorBenchmarkConfig
from friday.app.perception.evaluation.schemas import BenchmarkBox, BenchmarkDetection


class AdapterUnavailableError(RuntimeError):
    """Raised when an optional detector cannot be loaded on this computer."""


class DetectorAdapter(Protocol):
    provider: str
    input_size: str

    def predict(self, image_path: Path) -> tuple[BenchmarkDetection, ...]: ...

    def close(self) -> None: ...


@dataclass(frozen=True, slots=True)
class DetectorAdapterSpec:
    key: str
    display_name: str
    model_path: Path | None
    factory: Callable[[tuple[str, ...]], DetectorAdapter]


def default_adapter_specs(
    config: DetectorBenchmarkConfig,
) -> tuple[DetectorAdapterSpec, ...]:
    return (
        DetectorAdapterSpec(
            key="yolo26n",
            display_name="YOLO26n",
            model_path=config.yolo_model_path,
            factory=lambda _classes: Yolo26OnnxAdapter(
                config.yolo_model_path,
                providers=config.providers,
                prediction_floor=config.prediction_floor,
            ),
        ),
        DetectorAdapterSpec(
            key="rfdetr_nano",
            display_name="RF-DETR Nano",
            model_path=config.rfdetr_model_path,
            factory=lambda _classes: RfDetrNanoAdapter(
                config.rfdetr_model_path,
                prediction_floor=config.prediction_floor,
                device=config.rfdetr_device,
            ),
        ),
        DetectorAdapterSpec(
            key="rtdetrv4_s",
            display_name="RT-DETRv4-S",
            model_path=config.rtdetrv4_model_path,
            factory=lambda classes: RtDetrv4OnnxAdapter(
                config.rtdetrv4_model_path,
                providers=config.providers,
                prediction_floor=config.prediction_floor,
                class_names=classes,
                default_input_size=config.rtdetrv4_input_size,
            ),
        ),
    )


class Yolo26OnnxAdapter:
    def __init__(
        self,
        model_path: Path,
        *,
        providers: tuple[str, ...],
        prediction_floor: float,
    ) -> None:
        try:
            self._detector = OnnxObjectDetector(
                model_path,
                providers=providers,
                confidence=prediction_floor,
            )
        except DetectionModelError as exc:
            raise AdapterUnavailableError(str(exc)) from exc
        self.provider = ", ".join(self._detector.providers)
        width, height = self._detector.input_size
        self.input_size = f"{width}x{height}"

    def predict(self, image_path: Path) -> tuple[BenchmarkDetection, ...]:
        try:
            import cv2  # type: ignore
        except ImportError as exc:
            raise AdapterUnavailableError(
                "opencv-python is required for YOLO26n."
            ) from exc
        frame = cv2.imread(str(image_path))
        if frame is None:
            raise RuntimeError(f"Could not decode benchmark image: {image_path}")
        return tuple(
            BenchmarkDetection(
                label=detection.label,
                confidence=detection.confidence,
                box=BenchmarkBox(
                    x1=detection.box.x1,
                    y1=detection.box.y1,
                    x2=detection.box.x2,
                    y2=detection.box.y2,
                ),
            )
            for detection in self._detector.detect(frame)
        )

    def close(self) -> None:
        self._detector = None  # type: ignore[assignment]


class RfDetrNanoAdapter:
    def __init__(
        self,
        model_path: Path | None,
        *,
        prediction_floor: float,
        device: str,
    ) -> None:
        if model_path is None:
            raise AdapterUnavailableError(
                "Set FRIDAY_BENCHMARK_RFDETR_MODEL to a local RF-DETR Nano checkpoint."
            )
        if not model_path.is_file():
            raise AdapterUnavailableError(
                f"RF-DETR checkpoint was not found: {model_path}"
            )
        try:
            from rfdetr import RFDETRNano  # type: ignore
        except ImportError as exc:
            raise AdapterUnavailableError(
                "Install the optional rfdetr package before benchmarking RF-DETR Nano."
            ) from exc
        options: dict[str, Any] = {"pretrain_weights": str(model_path)}
        if device and device.casefold() != "auto":
            options["device"] = device
        try:
            self._model = RFDETRNano(**options)
        except Exception as exc:
            raise AdapterUnavailableError(
                f"Could not initialize RF-DETR Nano: {exc}"
            ) from exc
        self._prediction_floor = prediction_floor
        self._class_names = getattr(self._model, "class_names", {})
        self.provider = device if device.casefold() != "auto" else "rfdetr auto"
        self.input_size = "native"

    def predict(self, image_path: Path) -> tuple[BenchmarkDetection, ...]:
        detections = self._model.predict(
            str(image_path),
            threshold=self._prediction_floor,
        )
        boxes = getattr(detections, "xyxy", ())
        confidences = getattr(detections, "confidence", ())
        class_ids = getattr(detections, "class_id", ())
        results: list[BenchmarkDetection] = []
        for raw_box, raw_confidence, raw_class_id in zip(
            boxes,
            confidences,
            class_ids,
            strict=True,
        ):
            class_id = int(raw_class_id)
            x1, y1, x2, y2 = (float(value) for value in raw_box)
            if x2 <= x1 or y2 <= y1:
                continue
            results.append(
                BenchmarkDetection(
                    label=self._label_for(class_id),
                    confidence=float(raw_confidence),
                    box=BenchmarkBox(x1=x1, y1=y1, x2=x2, y2=y2),
                )
            )
        return tuple(sorted(results, key=lambda item: item.confidence, reverse=True))

    def close(self) -> None:
        self._model = None

    def _label_for(self, class_id: int) -> str:
        if isinstance(self._class_names, dict):
            return str(
                self._class_names.get(class_id)
                or self._class_names.get(str(class_id))
                or f"class_{class_id}"
            )
        if isinstance(self._class_names, (list, tuple)) and 0 <= class_id < len(
            self._class_names
        ):
            return str(self._class_names[class_id])
        return f"class_{class_id}"


class RtDetrv4OnnxAdapter:
    def __init__(
        self,
        model_path: Path | None,
        *,
        providers: tuple[str, ...],
        prediction_floor: float,
        class_names: tuple[str, ...],
        default_input_size: int,
    ) -> None:
        if model_path is None:
            raise AdapterUnavailableError(
                "Set FRIDAY_BENCHMARK_RTDETRV4_MODEL to a local RT-DETRv4-S ONNX model."
            )
        if not model_path.is_file():
            raise AdapterUnavailableError(
                f"RT-DETRv4-S model was not found: {model_path}"
            )
        try:
            import onnxruntime as ort  # type: ignore
        except ImportError as exc:
            raise AdapterUnavailableError(
                "onnxruntime is required for RT-DETRv4-S benchmarking."
            ) from exc
        available = set(ort.get_available_providers())
        selected = [provider for provider in providers if provider in available]
        if not selected and "CPUExecutionProvider" in available:
            selected = ["CPUExecutionProvider"]
        if not selected:
            raise AdapterUnavailableError(
                "No compatible ONNX Runtime provider is available."
            )
        try:
            self._session = ort.InferenceSession(str(model_path), providers=selected)
        except Exception as exc:
            raise AdapterUnavailableError(
                f"Could not initialize RT-DETRv4-S ONNX: {exc}"
            ) from exc
        inputs = self._session.get_inputs()
        self._image_input = next(
            (item for item in inputs if "image" in item.name.casefold()),
            inputs[0],
        )
        self._size_input = next(
            (item for item in inputs if "size" in item.name.casefold()),
            None,
        )
        self._output_names = [item.name for item in self._session.get_outputs()]
        shape = self._image_input.shape
        self._input_height = _static_dimension(shape, 2, default_input_size)
        self._input_width = _static_dimension(shape, 3, default_input_size)
        self._prediction_floor = prediction_floor
        self._class_names = class_names
        self.provider = ", ".join(self._session.get_providers())
        self.input_size = f"{self._input_width}x{self._input_height}"

    def predict(self, image_path: Path) -> tuple[BenchmarkDetection, ...]:
        try:
            import cv2  # type: ignore
            import numpy as np
        except ImportError as exc:
            raise AdapterUnavailableError(
                "opencv-python and numpy are required for RT-DETRv4-S."
            ) from exc
        frame = cv2.imread(str(image_path))
        if frame is None:
            raise RuntimeError(f"Could not decode benchmark image: {image_path}")
        frame_height, frame_width = frame.shape[:2]
        resized = cv2.resize(frame, (self._input_width, self._input_height))
        tensor = resized[:, :, ::-1].transpose(2, 0, 1)
        tensor = np.ascontiguousarray(tensor, dtype=np.float32)[None, ...] / 255.0
        feed: dict[str, Any] = {self._image_input.name: tensor}
        if self._size_input is not None:
            size_dtype = np.int32 if "int32" in self._size_input.type else np.int64
            feed[self._size_input.name] = np.asarray(
                [[frame_height, frame_width]],
                dtype=size_dtype,
            )
        raw_outputs = self._session.run(self._output_names, feed)
        output_map = {
            name.casefold(): np.asarray(value)
            for name, value in zip(self._output_names, raw_outputs, strict=True)
        }
        labels = _named_output(
            output_map, "label", fallback_index=0, values=raw_outputs
        )
        boxes = _named_output(output_map, "box", fallback_index=1, values=raw_outputs)
        scores = _named_output(
            output_map, "score", fallback_index=2, values=raw_outputs
        )
        labels = np.asarray(labels).reshape(-1)
        boxes = np.asarray(boxes).reshape(-1, 4)
        scores = np.asarray(scores).reshape(-1)
        results: list[BenchmarkDetection] = []
        for raw_class_id, raw_box, raw_score in zip(labels, boxes, scores, strict=True):
            score = float(raw_score)
            if score < self._prediction_floor:
                continue
            class_id = int(raw_class_id)
            x1, y1, x2, y2 = (float(value) for value in raw_box)
            if max(abs(x1), abs(y1), abs(x2), abs(y2)) <= 2.0:
                x1, x2 = x1 * frame_width, x2 * frame_width
                y1, y2 = y1 * frame_height, y2 * frame_height
            x1, x2 = sorted(
                (
                    max(0.0, min(float(frame_width), x1)),
                    max(0.0, min(float(frame_width), x2)),
                )
            )
            y1, y2 = sorted(
                (
                    max(0.0, min(float(frame_height), y1)),
                    max(0.0, min(float(frame_height), y2)),
                )
            )
            if x2 <= x1 or y2 <= y1:
                continue
            results.append(
                BenchmarkDetection(
                    label=self._label_for(class_id),
                    confidence=max(0.0, min(1.0, score)),
                    box=BenchmarkBox(x1=x1, y1=y1, x2=x2, y2=y2),
                )
            )
        return tuple(sorted(results, key=lambda item: item.confidence, reverse=True))

    def close(self) -> None:
        self._session = None  # type: ignore[assignment]

    def _label_for(self, class_id: int) -> str:
        if 0 <= class_id < len(self._class_names):
            return self._class_names[class_id]
        return f"class_{class_id}"


def _static_dimension(shape: list[Any], index: int, default: int) -> int:
    try:
        value = int(shape[index])
    except (IndexError, TypeError, ValueError):
        return default
    return value if value > 0 else default


def _named_output(
    output_map: dict[str, Any],
    fragment: str,
    *,
    fallback_index: int,
    values: list[Any],
) -> Any:
    for name, value in output_map.items():
        if fragment in name:
            return value
    if fallback_index >= len(values):
        raise RuntimeError(f"RT-DETRv4-S output '{fragment}' is missing.")
    return values[fallback_index]
