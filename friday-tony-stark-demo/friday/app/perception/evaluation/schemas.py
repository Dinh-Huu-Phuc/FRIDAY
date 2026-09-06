from __future__ import annotations

from enum import Enum
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator


class BenchmarkStatus(str, Enum):
    COMPLETED = "completed"
    UNAVAILABLE = "unavailable"
    FAILED = "failed"


class BenchmarkBox(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    x1: float = Field(ge=0.0)
    y1: float = Field(ge=0.0)
    x2: float = Field(gt=0.0)
    y2: float = Field(gt=0.0)

    @model_validator(mode="after")
    def validate_geometry(self) -> BenchmarkBox:
        if self.x2 <= self.x1 or self.y2 <= self.y1:
            raise ValueError("Benchmark boxes must have positive width and height.")
        return self

    @property
    def area(self) -> float:
        return (self.x2 - self.x1) * (self.y2 - self.y1)

    def iou(self, other: BenchmarkBox) -> float:
        intersection_width = max(0.0, min(self.x2, other.x2) - max(self.x1, other.x1))
        intersection_height = max(
            0.0,
            min(self.y2, other.y2) - max(self.y1, other.y1),
        )
        intersection = intersection_width * intersection_height
        union = self.area + other.area - intersection
        return intersection / union if union > 0.0 else 0.0


class GroundTruth(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)

    label: str = Field(min_length=1, max_length=100)
    box: BenchmarkBox


class BenchmarkDetection(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)

    label: str = Field(min_length=1, max_length=100)
    confidence: float = Field(ge=0.0, le=1.0)
    box: BenchmarkBox


class EvaluationSample(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    image_id: int = Field(gt=0)
    file_path: Path
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    ground_truth: tuple[GroundTruth, ...]


class EvaluationDataset(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    root: Path
    manifest_path: Path
    role: str
    samples: tuple[EvaluationSample, ...]
    class_names: tuple[str, ...]
    fingerprint: str = Field(min_length=64, max_length=64)
    total_boxes: int = Field(ge=0)
    warnings: tuple[str, ...] = ()


class PerClassMetrics(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    label: str
    ground_truth_count: int = Field(ge=0)
    prediction_count: int = Field(ge=0)
    precision: float = Field(ge=0.0, le=1.0)
    recall: float = Field(ge=0.0, le=1.0)
    ap50: float = Field(ge=0.0, le=1.0)
    map50_95: float = Field(ge=0.0, le=1.0)


class MetricSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    ground_truth_count: int = Field(ge=0)
    prediction_count: int = Field(ge=0)
    precision: float = Field(ge=0.0, le=1.0)
    recall: float = Field(ge=0.0, le=1.0)
    f1: float = Field(ge=0.0, le=1.0)
    ap50: float = Field(ge=0.0, le=1.0)
    map50_95: float = Field(ge=0.0, le=1.0)
    per_class: tuple[PerClassMetrics, ...]


class DetectorComparisonResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    model_key: str
    display_name: str
    status: BenchmarkStatus
    dataset_fingerprint: str = ""
    license_id: str = ""
    license_status: str = ""
    production_compatible: bool = False
    model_path: str = ""
    provider: str = ""
    input_size: str = ""
    images: int = Field(default=0, ge=0)
    ground_truth_count: int = Field(default=0, ge=0)
    prediction_count: int = Field(default=0, ge=0)
    precision: float = Field(default=0.0, ge=0.0, le=1.0)
    recall: float = Field(default=0.0, ge=0.0, le=1.0)
    f1: float = Field(default=0.0, ge=0.0, le=1.0)
    ap50: float = Field(default=0.0, ge=0.0, le=1.0)
    map50_95: float = Field(default=0.0, ge=0.0, le=1.0)
    average_latency_ms: float = Field(default=0.0, ge=0.0)
    p95_latency_ms: float = Field(default=0.0, ge=0.0)
    fps: float = Field(default=0.0, ge=0.0)
    note: str = ""
    per_class: tuple[PerClassMetrics, ...] = ()


class DetectorComparisonReport(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: int = 1
    generated_at: str
    dataset_manifest: str
    dataset_root: str
    dataset_role: str
    dataset_fingerprint: str
    license_policy: str
    images: int = Field(ge=0)
    ground_truth_count: int = Field(ge=0)
    confidence_threshold: float = Field(ge=0.0, le=1.0)
    iou_thresholds: tuple[float, ...]
    metric_method: str
    results: tuple[DetectorComparisonResult, ...]
    eligible_for_recommendation: bool
    recommended_model: str = ""
    recommendation_reason: str = ""
    warnings: tuple[str, ...] = ()
