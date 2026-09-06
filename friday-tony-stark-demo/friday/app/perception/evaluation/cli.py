from __future__ import annotations

import argparse
from dataclasses import replace
from pathlib import Path

from friday.app.perception.evaluation.config import DetectorBenchmarkConfig
from friday.app.perception.evaluation.dataset import EvaluationDatasetError
from friday.app.perception.evaluation.schemas import BenchmarkStatus
from friday.app.perception.evaluation.service import DetectorBenchmarkService


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="friday-detector-benchmark",
        description=(
            "Compare YOLO26n, RF-DETR Nano, and RT-DETRv4-S on the same "
            "human-reviewed COCO dataset."
        ),
    )
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--dataset-root", type=Path)
    parser.add_argument(
        "--dataset-role",
        choices=("approved", "validation", "test"),
    )
    parser.add_argument("--report-dir", type=Path)
    parser.add_argument("--max-images", type=int)
    parser.add_argument("--confidence", type=float)
    parser.add_argument("--yolo-model", type=Path)
    parser.add_argument("--rfdetr-model", type=Path)
    parser.add_argument("--rtdetrv4-model", type=Path)
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Return a failure status unless all three models complete.",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    config = DetectorBenchmarkConfig.from_environment()
    updates = {
        "manifest_path": args.manifest.resolve()
        if args.manifest
        else config.manifest_path,
        "dataset_root": (
            args.dataset_root.resolve() if args.dataset_root else config.dataset_root
        ),
        "dataset_role": args.dataset_role or config.dataset_role,
        "report_dir": args.report_dir.resolve()
        if args.report_dir
        else config.report_dir,
        "max_images": args.max_images
        if args.max_images is not None
        else config.max_images,
        "operating_confidence": (
            args.confidence
            if args.confidence is not None
            else config.operating_confidence
        ),
        "yolo_model_path": (
            args.yolo_model.resolve() if args.yolo_model else config.yolo_model_path
        ),
        "rfdetr_model_path": (
            args.rfdetr_model.resolve()
            if args.rfdetr_model
            else config.rfdetr_model_path
        ),
        "rtdetrv4_model_path": (
            args.rtdetrv4_model.resolve()
            if args.rtdetrv4_model
            else config.rtdetrv4_model_path
        ),
    }
    config = replace(config, **updates)
    if config.max_images < 0:
        raise SystemExit("--max-images cannot be negative.")
    if not 0.0 <= config.operating_confidence <= 1.0:
        raise SystemExit("--confidence must be between 0.0 and 1.0.")

    service = DetectorBenchmarkService(config)
    try:
        report = service.run()
        json_path, markdown_path = service.write_reports(report)
    except (EvaluationDatasetError, OSError, ValueError) as exc:
        raise SystemExit(f"Detector benchmark failed: {exc}") from exc

    print("MODEL             STATUS        mAP50:95   AP50      AVG MS    FPS")
    for result in report.results:
        print(
            f"{result.display_name:<17} {result.status.value:<13} "
            f"{result.map50_95:>8.4f}   {result.ap50:>6.4f}   "
            f"{result.average_latency_ms:>7.2f}   {result.fps:>6.2f}"
        )
        if result.note:
            print(f"  {result.note}")
    print(f"Dataset fingerprint: {report.dataset_fingerprint}")
    print(f"License policy: {report.license_policy}")
    print(f"JSON report: {json_path}")
    print(f"Markdown report: {markdown_path}")
    print(report.recommendation_reason)
    if args.strict and any(
        result.status != BenchmarkStatus.COMPLETED for result in report.results
    ):
        raise SystemExit(2)


if __name__ == "__main__":
    main()
