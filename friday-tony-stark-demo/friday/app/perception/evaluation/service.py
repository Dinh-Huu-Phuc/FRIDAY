from __future__ import annotations

import gc
import math
import os
from collections.abc import Iterable
from contextlib import suppress
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter
from uuid import uuid4

from friday.app.perception.evaluation.adapters import (
    AdapterUnavailableError,
    DetectorAdapter,
    DetectorAdapterSpec,
    default_adapter_specs,
)
from friday.app.perception.evaluation.config import DetectorBenchmarkConfig
from friday.app.perception.evaluation.dataset import load_coco_dataset
from friday.app.perception.evaluation.metrics import evaluate_detections
from friday.app.perception.evaluation.schemas import (
    BenchmarkDetection,
    BenchmarkStatus,
    DetectorComparisonReport,
    DetectorComparisonResult,
    EvaluationDataset,
)
from friday.app.perception.licensing.policy import evaluate_model_license


class DetectorBenchmarkService:
    def __init__(
        self,
        config: DetectorBenchmarkConfig | None = None,
        *,
        adapter_specs: Iterable[DetectorAdapterSpec] | None = None,
    ) -> None:
        self.config = config or DetectorBenchmarkConfig.from_environment()
        self.adapter_specs = tuple(
            adapter_specs
            if adapter_specs is not None
            else default_adapter_specs(self.config)
        )

    def run(self) -> DetectorComparisonReport:
        dataset = load_coco_dataset(
            self.config.manifest_path,
            dataset_root=self.config.dataset_root,
            role=self.config.dataset_role,
            max_images=self.config.max_images,
        )
        results = tuple(
            self._evaluate_model(spec, dataset) for spec in self.adapter_specs
        )
        eligible, recommendation, reason, warnings = self._recommend(dataset, results)
        return DetectorComparisonReport(
            generated_at=datetime.now(UTC).isoformat(),
            dataset_manifest=str(dataset.manifest_path),
            dataset_root=str(dataset.root),
            dataset_role=dataset.role,
            dataset_fingerprint=dataset.fingerprint,
            license_policy=self.config.license_policy.value,
            images=len(dataset.samples),
            ground_truth_count=dataset.total_boxes,
            confidence_threshold=self.config.operating_confidence,
            iou_thresholds=self.config.iou_thresholds,
            metric_method=(
                "FRIDAY framework-neutral 101-point interpolated AP; macro average "
                "across reviewed classes and IoU 0.50:0.95"
            ),
            results=results,
            eligible_for_recommendation=eligible,
            recommended_model=recommendation,
            recommendation_reason=reason,
            warnings=(*dataset.warnings, *warnings),
        )

    def write_reports(
        self,
        report: DetectorComparisonReport,
    ) -> tuple[Path, Path]:
        directory = self.config.report_dir
        directory.mkdir(parents=True, exist_ok=True)
        json_path = directory / "detector_comparison_latest.json"
        markdown_path = directory / "detector_comparison_latest.md"
        _atomic_write(json_path, report.model_dump_json(indent=2) + "\n")
        _atomic_write(markdown_path, _markdown_report(report))
        return json_path, markdown_path

    def _evaluate_model(
        self,
        spec: DetectorAdapterSpec,
        dataset: EvaluationDataset,
    ) -> DetectorComparisonResult:
        model_path = str(spec.model_path) if spec.model_path is not None else ""
        license_decision = evaluate_model_license(
            spec.key,
            policy=self.config.license_policy,
            enterprise_evidence_path=self.config.enterprise_evidence_path,
        )
        license_fields = {
            "license_id": license_decision.effective_license,
            "license_status": license_decision.status.value,
            "production_compatible": license_decision.compatible,
        }
        adapter: DetectorAdapter | None = None
        try:
            adapter = spec.factory(dataset.class_names)
        except AdapterUnavailableError as exc:
            return DetectorComparisonResult(
                model_key=spec.key,
                display_name=spec.display_name,
                status=BenchmarkStatus.UNAVAILABLE,
                dataset_fingerprint=dataset.fingerprint,
                model_path=model_path,
                note=str(exc),
                **license_fields,
            )
        except Exception as exc:  # noqa: BLE001 - isolate one optional model adapter
            return DetectorComparisonResult(
                model_key=spec.key,
                display_name=spec.display_name,
                status=BenchmarkStatus.FAILED,
                dataset_fingerprint=dataset.fingerprint,
                model_path=model_path,
                note=f"Adapter initialization failed: {exc}",
                **license_fields,
            )

        try:
            for _ in range(self.config.warmup_iterations):
                adapter.predict(dataset.samples[0].file_path)
            predictions: dict[int, tuple[BenchmarkDetection, ...]] = {}
            latencies: list[float] = []
            for sample in dataset.samples:
                started = perf_counter()
                predictions[sample.image_id] = adapter.predict(sample.file_path)
                latencies.append((perf_counter() - started) * 1000.0)
            metrics = evaluate_detections(
                dataset,
                predictions,
                operating_confidence=self.config.operating_confidence,
                iou_thresholds=self.config.iou_thresholds,
            )
            average_latency = sum(latencies) / len(latencies)
            return DetectorComparisonResult(
                model_key=spec.key,
                display_name=spec.display_name,
                status=BenchmarkStatus.COMPLETED,
                dataset_fingerprint=dataset.fingerprint,
                model_path=model_path,
                provider=adapter.provider,
                input_size=adapter.input_size,
                images=len(dataset.samples),
                ground_truth_count=metrics.ground_truth_count,
                prediction_count=metrics.prediction_count,
                precision=metrics.precision,
                recall=metrics.recall,
                f1=metrics.f1,
                ap50=metrics.ap50,
                map50_95=metrics.map50_95,
                average_latency_ms=average_latency,
                p95_latency_ms=_percentile_95(latencies),
                fps=1000.0 / average_latency if average_latency > 0.0 else 0.0,
                per_class=metrics.per_class,
                **license_fields,
            )
        except Exception as exc:  # noqa: BLE001 - preserve results from other models
            return DetectorComparisonResult(
                model_key=spec.key,
                display_name=spec.display_name,
                status=BenchmarkStatus.FAILED,
                dataset_fingerprint=dataset.fingerprint,
                model_path=model_path,
                provider=adapter.provider,
                input_size=adapter.input_size,
                note=f"Benchmark inference failed: {exc}",
                **license_fields,
            )
        finally:
            with suppress(Exception):
                adapter.close()
            gc.collect()
            _release_cuda_cache()

    def _recommend(
        self,
        dataset: EvaluationDataset,
        results: tuple[DetectorComparisonResult, ...],
    ) -> tuple[bool, str, str, list[str]]:
        warnings: list[str] = []
        completed = [
            result for result in results if result.status == BenchmarkStatus.COMPLETED
        ]
        compatible_completed = [
            result for result in completed if result.production_compatible
        ]
        expected_models = {"yolo26n", "rfdetr_nano", "rtdetrv4_s"}
        result_models = {result.model_key for result in results}
        fingerprints_match = all(
            result.dataset_fingerprint == dataset.fingerprint for result in results
        )
        if dataset.role not in {"validation", "test"}:
            warnings.append(
                "Use a held-out validation or test manifest before selecting a model."
            )
        if len(dataset.samples) < self.config.minimum_recommendation_images:
            warnings.append(
                "Dataset has "
                f"{len(dataset.samples)} images; at least "
                f"{self.config.minimum_recommendation_images} are required for a recommendation."
            )
        if (
            len(completed) != len(results)
            or len(results) != 3
            or result_models != expected_models
        ):
            warnings.append(
                "A recommendation requires completed results for YOLO26n, "
                "RF-DETR Nano, and RT-DETRv4-S."
            )
        if not fingerprints_match:
            warnings.append(
                "Model results do not share the loaded dataset fingerprint."
            )
        if not compatible_completed:
            warnings.append(
                f"No completed model is compatible with {self.config.license_policy.value}."
            )
        eligible = (
            dataset.role in {"validation", "test"}
            and len(dataset.samples) >= self.config.minimum_recommendation_images
            and len(results) == 3
            and len(completed) == 3
            and result_models == expected_models
            and fingerprints_match
            and bool(compatible_completed)
        )
        if not eligible:
            return False, "", "No production recommendation was made.", warnings
        performance_winner = max(
            completed,
            key=lambda result: (result.map50_95, -result.average_latency_ms),
        )
        winner = max(
            compatible_completed,
            key=lambda result: (result.map50_95, -result.average_latency_ms),
        )
        if performance_winner.model_key != winner.model_key:
            warnings.append(
                f"{performance_winner.display_name} led the raw benchmark but was "
                f"excluded by {self.config.license_policy.value}."
            )
        reason = (
            f"{winner.display_name} achieved the highest compatible mAP50:95 "
            f"({winner.map50_95:.4f}) under {self.config.license_policy.value}; "
            "latency breaks metric ties."
        )
        return True, winner.model_key, reason, warnings


def _percentile_95(values: list[float]) -> float:
    ordered = sorted(values)
    if not ordered:
        return 0.0
    index = max(0, math.ceil(len(ordered) * 0.95) - 1)
    return ordered[index]


def _release_cuda_cache() -> None:
    try:
        import torch  # type: ignore
    except ImportError:
        return
    if torch.cuda.is_available():
        torch.cuda.empty_cache()


def _atomic_write(path: Path, content: str) -> None:
    temporary = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    try:
        temporary.write_text(content, encoding="utf-8")
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _markdown_report(report: DetectorComparisonReport) -> str:
    lines = [
        "# FRIDAY Detector Comparison",
        "",
        f"- Generated: `{report.generated_at}`",
        f"- Dataset role: `{report.dataset_role}`",
        f"- Images: `{report.images}`",
        f"- Ground-truth boxes: `{report.ground_truth_count}`",
        f"- Dataset fingerprint: `{report.dataset_fingerprint}`",
        f"- License policy: `{report.license_policy}`",
        f"- Metric: {report.metric_method}",
        "",
        "| Model | Status | License | Compatible | mAP50:95 | AP50 | Precision | Recall | Avg ms | P95 ms | FPS | Provider |",
        "| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for result in report.results:
        lines.append(
            f"| {result.display_name} | {result.status.value} | "
            f"{result.license_id or '-'} | "
            f"{str(result.production_compatible).lower()} | "
            f"{result.map50_95:.4f} | {result.ap50:.4f} | "
            f"{result.precision:.4f} | {result.recall:.4f} | "
            f"{result.average_latency_ms:.2f} | {result.p95_latency_ms:.2f} | "
            f"{result.fps:.2f} | {result.provider or '-'} |"
        )
        if result.note:
            lines.append(f"\n{result.display_name}: {result.note}\n")
    lines.extend(
        [
            "",
            "## Recommendation",
            "",
            (
                f"Recommended model: `{report.recommended_model}`. "
                f"{report.recommendation_reason}"
                if report.eligible_for_recommendation
                else report.recommendation_reason
            ),
        ]
    )
    if report.warnings:
        lines.extend(("", "## Warnings", ""))
        lines.extend(f"- {warning}" for warning in report.warnings)
    lines.append("")
    return "\n".join(lines)
