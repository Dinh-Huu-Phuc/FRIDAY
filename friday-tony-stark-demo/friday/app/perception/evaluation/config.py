from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from friday.app.perception.licensing.config import VisionLicenseConfig
from friday.app.perception.licensing.schemas import VisionLicensePolicy


@dataclass(frozen=True, slots=True)
class DetectorBenchmarkConfig:
    dataset_root: Path
    manifest_path: Path
    report_dir: Path
    dataset_role: str
    operating_confidence: float
    prediction_floor: float
    iou_thresholds: tuple[float, ...]
    max_images: int
    warmup_iterations: int
    minimum_recommendation_images: int
    providers: tuple[str, ...]
    yolo_model_path: Path
    rfdetr_model_path: Path | None
    rtdetrv4_model_path: Path | None
    rfdetr_device: str
    rtdetrv4_input_size: int
    license_policy: VisionLicensePolicy
    enterprise_evidence_path: Path | None

    @classmethod
    def from_environment(cls) -> DetectorBenchmarkConfig:
        project_root = Path(__file__).resolve().parents[4]
        license_config = VisionLicenseConfig.from_environment()
        default_dataset_root = project_root / "friday" / "trainModel" / "vision"
        annotation_root = _environment_path(
            "FRIDAY_VISION_ANNOTATION_ROOT",
            default_dataset_root,
        )
        dataset_root = _environment_path(
            "FRIDAY_BENCHMARK_DATASET_ROOT",
            annotation_root,
        )
        manifest_path = _environment_path(
            "FRIDAY_BENCHMARK_COCO_MANIFEST",
            dataset_root / "annotations" / "approved" / "coco.json",
        )
        report_dir = _environment_path(
            "FRIDAY_BENCHMARK_REPORT_DIR",
            dataset_root / "evaluation" / "reports",
        )
        providers = tuple(
            value.strip()
            for value in (
                os.getenv("FRIDAY_VISION_EXECUTION_PROVIDERS")
                or "CUDAExecutionProvider,CPUExecutionProvider"
            ).split(",")
            if value.strip()
        )
        role = (
            (os.getenv("FRIDAY_BENCHMARK_DATASET_ROLE") or "approved").strip().lower()
        )
        if role not in {"approved", "validation", "test"}:
            role = "approved"
        return cls(
            dataset_root=dataset_root,
            manifest_path=manifest_path,
            report_dir=report_dir,
            dataset_role=role,
            operating_confidence=_environment_float(
                "FRIDAY_BENCHMARK_CONFIDENCE",
                default=0.25,
                minimum=0.0,
                maximum=1.0,
            ),
            prediction_floor=_environment_float(
                "FRIDAY_BENCHMARK_PREDICTION_FLOOR",
                default=0.001,
                minimum=0.0,
                maximum=1.0,
            ),
            iou_thresholds=tuple(round(0.5 + step * 0.05, 2) for step in range(10)),
            max_images=_environment_int(
                "FRIDAY_BENCHMARK_MAX_IMAGES",
                default=0,
                minimum=0,
                maximum=1_000_000,
            ),
            warmup_iterations=_environment_int(
                "FRIDAY_BENCHMARK_WARMUP_ITERATIONS",
                default=1,
                minimum=0,
                maximum=20,
            ),
            minimum_recommendation_images=_environment_int(
                "FRIDAY_BENCHMARK_MIN_RECOMMENDATION_IMAGES",
                default=50,
                minimum=1,
                maximum=1_000_000,
            ),
            providers=providers or ("CPUExecutionProvider",),
            yolo_model_path=_environment_path(
                "FRIDAY_BENCHMARK_YOLO_MODEL",
                project_root
                / "friday"
                / "assets"
                / "models"
                / "vision"
                / "yolo26n.onnx",
            ),
            rfdetr_model_path=_optional_environment_path(
                "FRIDAY_BENCHMARK_RFDETR_MODEL"
            ),
            rtdetrv4_model_path=_optional_environment_path(
                "FRIDAY_BENCHMARK_RTDETRV4_MODEL"
            ),
            rfdetr_device=(
                os.getenv("FRIDAY_BENCHMARK_RFDETR_DEVICE") or "auto"
            ).strip(),
            rtdetrv4_input_size=_environment_int(
                "FRIDAY_BENCHMARK_RTDETRV4_INPUT_SIZE",
                default=640,
                minimum=128,
                maximum=2048,
            ),
            license_policy=license_config.policy,
            enterprise_evidence_path=license_config.enterprise_evidence_path,
        )


def _environment_path(name: str, default: Path) -> Path:
    configured = (os.getenv(name) or "").strip()
    return (Path(configured).expanduser() if configured else default).resolve()


def _optional_environment_path(name: str) -> Path | None:
    configured = (os.getenv(name) or "").strip()
    return Path(configured).expanduser().resolve() if configured else None


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
