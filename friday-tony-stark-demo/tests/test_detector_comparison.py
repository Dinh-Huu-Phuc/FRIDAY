from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from friday.app.perception.evaluation import (
    AdapterUnavailableError,
    BenchmarkBox,
    BenchmarkDetection,
    BenchmarkStatus,
    DetectorAdapterSpec,
    DetectorBenchmarkConfig,
    DetectorBenchmarkService,
    EvaluationDatasetError,
    evaluate_detections,
    load_coco_dataset,
)
from friday.app.perception.evaluation.adapters import Yolo26OnnxAdapter
from friday.app.perception.licensing import VisionLicensePolicy


class FakeAdapter:
    provider = "test"
    input_size = "64x64"

    def __init__(self, predictions: tuple[BenchmarkDetection, ...]) -> None:
        self.predictions = predictions
        self.closed = False

    def predict(self, image_path: Path) -> tuple[BenchmarkDetection, ...]:
        assert image_path.is_file()
        return self.predictions

    def close(self) -> None:
        self.closed = True


def test_coco_loader_is_deterministic_and_fingerprints_image_bytes(
    tmp_path: Path,
) -> None:
    manifest = _write_dataset(tmp_path)
    first = load_coco_dataset(
        manifest,
        dataset_root=tmp_path,
        role="validation",
    )
    second = load_coco_dataset(
        manifest,
        dataset_root=tmp_path,
        role="validation",
    )

    assert first.fingerprint == second.fingerprint
    assert first.total_boxes == 1
    assert first.class_names == ("person",)

    (tmp_path / "images" / "sample.jpg").write_bytes(b"changed-image")
    changed = load_coco_dataset(
        manifest,
        dataset_root=tmp_path,
        role="validation",
    )
    assert changed.fingerprint != first.fingerprint


def test_coco_loader_rejects_images_outside_dataset_root(tmp_path: Path) -> None:
    outside = tmp_path.parent / "outside.jpg"
    outside.write_bytes(b"outside")
    manifest = _write_dataset(tmp_path, file_name="../outside.jpg")

    with pytest.raises(EvaluationDatasetError, match="escapes"):
        load_coco_dataset(manifest, dataset_root=tmp_path, role="test")


def test_shared_metrics_score_perfect_and_duplicate_predictions(tmp_path: Path) -> None:
    dataset = load_coco_dataset(
        _write_dataset(tmp_path),
        dataset_root=tmp_path,
        role="validation",
    )
    perfect = _person_detection(confidence=0.9)
    metrics = evaluate_detections(
        dataset,
        {1: (perfect,)},
        operating_confidence=0.25,
        iou_thresholds=tuple(round(0.5 + index * 0.05, 2) for index in range(10)),
    )
    assert metrics.precision == pytest.approx(1.0)
    assert metrics.recall == pytest.approx(1.0)
    assert metrics.ap50 == pytest.approx(1.0)
    assert metrics.map50_95 == pytest.approx(1.0)

    duplicate = evaluate_detections(
        dataset,
        {1: (perfect, _person_detection(confidence=0.8))},
        operating_confidence=0.25,
        iou_thresholds=(0.5,),
    )
    assert duplicate.precision == pytest.approx(0.5)
    assert duplicate.recall == pytest.approx(1.0)


def test_runner_records_unavailable_model_without_aborting(tmp_path: Path) -> None:
    config = _config(tmp_path, minimum_images=1)
    completed = DetectorAdapterSpec(
        key="yolo26n",
        display_name="YOLO26n",
        model_path=tmp_path / "yolo.onnx",
        factory=lambda _classes: FakeAdapter((_person_detection(),)),
    )

    def unavailable(_classes: tuple[str, ...]) -> FakeAdapter:
        raise AdapterUnavailableError("checkpoint missing")

    report = DetectorBenchmarkService(
        config,
        adapter_specs=(
            completed,
            DetectorAdapterSpec("rfdetr_nano", "RF-DETR Nano", None, unavailable),
            DetectorAdapterSpec("rtdetrv4_s", "RT-DETRv4-S", None, unavailable),
        ),
    ).run()

    assert report.results[0].status == BenchmarkStatus.COMPLETED
    assert report.results[1].status == BenchmarkStatus.UNAVAILABLE
    assert all(
        result.dataset_fingerprint == report.dataset_fingerprint
        for result in report.results
    )
    assert report.eligible_for_recommendation is False
    assert report.recommended_model == ""


def test_runner_recommends_only_after_all_fairness_gates_pass(tmp_path: Path) -> None:
    config = _config(tmp_path, minimum_images=1)
    perfect = _person_detection()
    wrong = BenchmarkDetection(
        label="person",
        confidence=0.9,
        box=BenchmarkBox(x1=0, y1=0, x2=5, y2=5),
    )
    specs = (
        DetectorAdapterSpec(
            "yolo26n",
            "YOLO26n",
            tmp_path / "yolo.onnx",
            lambda _classes: FakeAdapter((perfect,)),
        ),
        DetectorAdapterSpec(
            "rfdetr_nano",
            "RF-DETR Nano",
            tmp_path / "rf.pth",
            lambda _classes: FakeAdapter((wrong,)),
        ),
        DetectorAdapterSpec(
            "rtdetrv4_s",
            "RT-DETRv4-S",
            tmp_path / "rt.onnx",
            lambda _classes: FakeAdapter((wrong,)),
        ),
    )
    service = DetectorBenchmarkService(config, adapter_specs=specs)
    report = service.run()

    assert report.eligible_for_recommendation is True
    assert report.recommended_model == "yolo26n"
    json_report, markdown_report = service.write_reports(report)
    assert json.loads(json_report.read_text(encoding="utf-8"))["recommended_model"] == (
        "yolo26n"
    )
    assert "YOLO26n" in markdown_report.read_text(encoding="utf-8")


def test_mit_policy_excludes_yolo_from_recommendation(tmp_path: Path) -> None:
    config = replace(
        _config(tmp_path, minimum_images=1),
        license_policy=VisionLicensePolicy.MIT_DISTRIBUTION,
    )
    perfect = _person_detection()
    wrong = BenchmarkDetection(
        label="person",
        confidence=0.9,
        box=BenchmarkBox(x1=0, y1=0, x2=5, y2=5),
    )
    specs = (
        DetectorAdapterSpec(
            "yolo26n",
            "YOLO26n",
            tmp_path / "yolo.onnx",
            lambda _classes: FakeAdapter((perfect,)),
        ),
        DetectorAdapterSpec(
            "rfdetr_nano",
            "RF-DETR Nano",
            tmp_path / "rf.pth",
            lambda _classes: FakeAdapter((perfect,)),
        ),
        DetectorAdapterSpec(
            "rtdetrv4_s",
            "RT-DETRv4-S",
            tmp_path / "rt.onnx",
            lambda _classes: FakeAdapter((wrong,)),
        ),
    )

    report = DetectorBenchmarkService(config, adapter_specs=specs).run()

    assert report.recommended_model == "rfdetr_nano"
    assert report.results[0].production_compatible is False
    assert report.results[1].production_compatible is True


def test_real_yolo26n_onnx_adapter_smoke() -> None:
    project_root = Path(__file__).resolve().parents[1]
    adapter = Yolo26OnnxAdapter(
        project_root / "friday" / "assets" / "models" / "vision" / "yolo26n.onnx",
        providers=("CPUExecutionProvider",),
        prediction_floor=0.25,
    )
    try:
        detections = adapter.predict(
            project_root / "friday" / "assets" / "img" / "Friday.jpg"
        )
    finally:
        adapter.close()

    assert isinstance(detections, tuple)
    assert "CPUExecutionProvider" in adapter.provider


def _write_dataset(tmp_path: Path, *, file_name: str = "images/sample.jpg") -> Path:
    image_path = (tmp_path / file_name).resolve()
    if ".." not in Path(file_name).parts:
        image_path.parent.mkdir(parents=True, exist_ok=True)
        image_path.write_bytes(b"synthetic-image")
    manifest = tmp_path / "annotations" / "coco.json"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(
        json.dumps(
            {
                "images": [
                    {
                        "id": 1,
                        "file_name": file_name,
                        "width": 64,
                        "height": 64,
                    }
                ],
                "annotations": [
                    {
                        "id": 1,
                        "image_id": 1,
                        "category_id": 1,
                        "bbox": [10, 10, 40, 40],
                    }
                ],
                "categories": [{"id": 1, "name": "person"}],
            }
        ),
        encoding="utf-8",
    )
    return manifest


def _person_detection(confidence: float = 0.9) -> BenchmarkDetection:
    return BenchmarkDetection(
        label="person",
        confidence=confidence,
        box=BenchmarkBox(x1=10, y1=10, x2=50, y2=50),
    )


def _config(tmp_path: Path, *, minimum_images: int) -> DetectorBenchmarkConfig:
    manifest = _write_dataset(tmp_path)
    return DetectorBenchmarkConfig(
        dataset_root=tmp_path,
        manifest_path=manifest,
        report_dir=tmp_path / "reports",
        dataset_role="validation",
        operating_confidence=0.25,
        prediction_floor=0.001,
        iou_thresholds=tuple(round(0.5 + index * 0.05, 2) for index in range(10)),
        max_images=0,
        warmup_iterations=0,
        minimum_recommendation_images=minimum_images,
        providers=("CPUExecutionProvider",),
        yolo_model_path=tmp_path / "yolo.onnx",
        rfdetr_model_path=None,
        rtdetrv4_model_path=None,
        rfdetr_device="cpu",
        rtdetrv4_input_size=640,
        license_policy=VisionLicensePolicy.PERSONAL_RESEARCH,
        enterprise_evidence_path=None,
    )
