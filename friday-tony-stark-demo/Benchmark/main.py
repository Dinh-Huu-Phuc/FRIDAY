from __future__ import annotations

import argparse
import json
import sys
from dataclasses import replace
from pathlib import Path


def _bootstrap_project_root() -> Path:
    locations = [Path.cwd(), Path(sys.executable).resolve().parent, Path(__file__).resolve().parent]
    for location in locations:
        for candidate in (location, *location.parents):
            if (candidate / "pyproject.toml").is_file() and (candidate / "friday").is_dir():
                if str(candidate) not in sys.path:
                    sys.path.insert(0, str(candidate))
                return candidate
    raise RuntimeError("Could not locate the FRIDAY project root.")


PROJECT_ROOT = _bootstrap_project_root()

from friday.core.hardware import (
    apply_decision_to_env,
    create_benchmark_report,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Inspect this computer and select a safe FRIDAY vision backend."
    )
    parser.add_argument("--project-root", type=Path, default=PROJECT_ROOT)
    parser.add_argument(
        "--no-apply-env",
        action="store_true",
        help="Show the decision without updating the project's .env file.",
    )
    parser.add_argument(
        "--no-pause",
        action="store_true",
        help="Exit immediately instead of waiting for Enter.",
    )
    return parser


def _print_report(report) -> None:
    hardware = report.hardware
    decision = report.decision
    print("\nFRIDAY VISION BENCHMARK")
    print("=" * 62)
    print(f"Project       : {report.project_root}")
    print(f"Operating OS  : {hardware.operating_system}")
    print(f"CPU           : {hardware.cpu_name}")
    print(f"CPU threads   : {hardware.logical_cpu_count}")
    memory = f"{hardware.system_memory_mb} MB" if hardware.system_memory_mb else "unknown"
    print(f"System memory : {memory}")
    if hardware.gpus:
        for index, gpu in enumerate(hardware.gpus, start=1):
            total = f"{gpu.total_memory_mb} MB" if gpu.total_memory_mb else "unknown VRAM"
            free = f", {gpu.free_memory_mb} MB free" if gpu.free_memory_mb else ""
            print(f"GPU {index:<9}: {gpu.name} ({total}{free})")
            if gpu.driver_version:
                print(f"GPU driver    : {gpu.driver_version} / compute {gpu.compute_capability or 'unknown'}")
    else:
        print("GPU           : no NVIDIA GPU reported")
    providers = ", ".join(hardware.onnx_providers) or "none detected"
    print(f"ONNX Runtime  : {hardware.onnx_runtime_version or 'not available'}")
    print(f"ORT providers : {providers}")
    print("-" * 62)
    print(f"Backend       : {decision.backend}")
    print(f"Profile       : {decision.profile}")
    print(f"Model policy  : {decision.detector_model}")
    print(f"Detector      : {decision.input_size}px at target {decision.detector_fps} FPS")
    print(f"Tracker       : target {decision.tracker_fps} FPS")
    print(f"Ollama preload: {'enabled' if decision.ollama_preload else 'disabled'}")
    if report.metrics.available:
        print(
            "Preprocess    : "
            f"{report.metrics.average_preprocess_ms} ms / {report.metrics.preprocess_fps} FPS"
        )
    else:
        print(f"Preprocess    : unavailable ({report.metrics.note})")
    print("\nDecision reasons:")
    for reason in decision.reasons:
        print(f"  + {reason}")
    if decision.warnings:
        print("\nWarnings:")
        for warning in decision.warnings:
            print(f"  ! {warning}")
    if report.applied_env_keys:
        print(f"\nUpdated .env : {len(report.applied_env_keys)} vision runtime keys")


def main() -> int:
    args = _parser().parse_args()
    project_root = args.project_root.resolve()
    report = create_benchmark_report(project_root)
    if not args.no_apply_env:
        keys = apply_decision_to_env(project_root / ".env", report.decision)
        report = replace(report, applied_env_keys=keys)

    report_dir = project_root / "Benchmark" / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / "friday_vision_benchmark_latest.json"
    report_path.write_text(
        json.dumps(report.to_dict(), ensure_ascii=True, indent=2) + "\n",
        encoding="utf-8",
    )
    _print_report(report)
    print(f"\nReport saved  : {report_path}")
    print("=" * 62)
    if getattr(sys, "frozen", False) and not args.no_pause:
        try:
            input("\nPress Enter to close...")
        except EOFError:
            pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
