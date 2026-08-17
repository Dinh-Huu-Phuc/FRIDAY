from __future__ import annotations

import ast
from pathlib import Path
from time import perf_counter
from typing import Any

from friday.app.perception.detection.schemas import BoundingBox, Detection


class DetectionModelError(RuntimeError):
    """Raised when the local object detector cannot be loaded or executed."""


class OnnxObjectDetector:
    def __init__(
        self,
        model_path: str | Path,
        *,
        providers: tuple[str, ...],
        confidence: float = 0.35,
    ) -> None:
        try:
            import onnxruntime as ort  # type: ignore
        except ImportError as exc:
            raise DetectionModelError("onnxruntime is required for object detection.") from exc

        self.model_path = Path(model_path)
        if not self.model_path.is_file():
            raise DetectionModelError(f"Detection model was not found: {self.model_path}")
        available = set(ort.get_available_providers())
        selected = [provider for provider in providers if provider in available]
        if not selected and "CPUExecutionProvider" in available:
            selected = ["CPUExecutionProvider"]
        if not selected:
            raise DetectionModelError("No compatible ONNX Runtime provider is available.")

        options = ort.SessionOptions()
        options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        self._session = ort.InferenceSession(
            str(self.model_path),
            sess_options=options,
            providers=selected,
        )
        model_input = self._session.get_inputs()[0]
        self._input_name = model_input.name
        shape = model_input.shape
        self._input_height = int(shape[2])
        self._input_width = int(shape[3])
        self._output_names = [item.name for item in self._session.get_outputs()]
        self._confidence = confidence
        self._class_names = self._read_class_names()
        self.providers = tuple(self._session.get_providers())
        self.last_inference_ms = 0.0

    @property
    def name(self) -> str:
        return self.model_path.stem

    def detect(self, frame: Any) -> tuple[Detection, ...]:
        try:
            import cv2  # type: ignore
            import numpy as np
        except ImportError as exc:
            raise DetectionModelError("opencv-python and numpy are required.") from exc

        if frame is None or not hasattr(frame, "shape") or len(frame.shape) < 3:
            return ()
        frame_height, frame_width = frame.shape[:2]
        scale = min(
            self._input_width / frame_width,
            self._input_height / frame_height,
        )
        resized_width = max(1, round(frame_width * scale))
        resized_height = max(1, round(frame_height * scale))
        resized = cv2.resize(
            frame,
            (resized_width, resized_height),
            interpolation=cv2.INTER_LINEAR,
        )
        pad_x = (self._input_width - resized_width) // 2
        pad_y = (self._input_height - resized_height) // 2
        canvas = np.full(
            (self._input_height, self._input_width, 3),
            114,
            dtype=np.uint8,
        )
        canvas[pad_y : pad_y + resized_height, pad_x : pad_x + resized_width] = resized
        tensor = canvas[:, :, ::-1].transpose(2, 0, 1)
        tensor = np.ascontiguousarray(tensor, dtype=np.float32) / 255.0
        tensor = tensor[None, ...]

        started = perf_counter()
        outputs = self._session.run(self._output_names, {self._input_name: tensor})
        self.last_inference_ms = (perf_counter() - started) * 1000
        predictions = np.asarray(outputs[0])
        if predictions.ndim == 3:
            predictions = predictions[0]
        if predictions.ndim != 2 or predictions.shape[1] < 6:
            raise DetectionModelError(
                f"Unsupported detector output shape: {tuple(predictions.shape)}"
            )

        detections: list[Detection] = []
        for row in predictions:
            confidence = float(row[4])
            if confidence < self._confidence:
                continue
            class_id = int(row[5])
            x1 = round((float(row[0]) - pad_x) / scale)
            y1 = round((float(row[1]) - pad_y) / scale)
            x2 = round((float(row[2]) - pad_x) / scale)
            y2 = round((float(row[3]) - pad_y) / scale)
            box = BoundingBox(
                x1=max(0, min(frame_width - 1, x1)),
                y1=max(0, min(frame_height - 1, y1)),
                x2=max(0, min(frame_width, x2)),
                y2=max(0, min(frame_height, y2)),
            )
            if box.width < 2 or box.height < 2:
                continue
            detections.append(
                Detection(
                    class_id=class_id,
                    label=self._class_names.get(class_id, f"class_{class_id}"),
                    confidence=confidence,
                    box=box,
                )
            )
        return tuple(sorted(detections, key=lambda item: item.confidence, reverse=True))

    def _read_class_names(self) -> dict[int, str]:
        metadata = self._session.get_modelmeta().custom_metadata_map
        raw_names = metadata.get("names", "")
        try:
            parsed = ast.literal_eval(raw_names)
        except (SyntaxError, ValueError):
            return {}
        if not isinstance(parsed, dict):
            return {}
        return {int(key): str(value) for key, value in parsed.items()}
