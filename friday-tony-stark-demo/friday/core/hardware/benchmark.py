from __future__ import annotations

import json
import subprocess
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

from friday.core.hardware.policy import decide_vision_runtime
from friday.core.hardware.probe import find_project_root, probe_hardware, project_python
from friday.core.hardware.schemas import (
    BenchmarkMetrics,
    VisionBenchmarkReport,
    VisionRuntimeDecision,
)


def run_preprocess_benchmark(project_root: Path, input_size: int) -> BenchmarkMetrics:
    python = project_python(project_root)
    if python is None:
        return BenchmarkMetrics(
            available=False,
            note="Project virtual environment was not found.",
        )
    script = f"""
import json, time
try:
    import cv2
    import numpy as np
    frame = np.zeros((720, 1280, 3), dtype=np.uint8)
    iterations = 40
    for _ in range(5):
        cv2.dnn.blobFromImage(frame, 1 / 255.0, ({input_size}, {input_size}), swapRB=True)
    started = time.perf_counter()
    for _ in range(iterations):
        cv2.dnn.blobFromImage(frame, 1 / 255.0, ({input_size}, {input_size}), swapRB=True)
    elapsed = time.perf_counter() - started
    print(json.dumps({{'ok': True, 'iterations': iterations, 'average_ms': elapsed * 1000 / iterations, 'fps': iterations / elapsed}}))
except Exception as exc:
    print(json.dumps({{'ok': False, 'error': type(exc).__name__ + ': ' + str(exc)}}))
"""
    try:
        completed = subprocess.run(
            [str(python), "-c", script],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        payload = json.loads(completed.stdout.strip().splitlines()[-1])
    except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError, IndexError) as exc:
        return BenchmarkMetrics(
            available=False,
            note=f"OpenCV preprocessing benchmark failed: {type(exc).__name__}.",
        )
    if not payload.get("ok"):
        return BenchmarkMetrics(available=False, note=str(payload.get("error") or "Unknown error"))
    return BenchmarkMetrics(
        available=True,
        iterations=int(payload["iterations"]),
        average_preprocess_ms=round(float(payload["average_ms"]), 3),
        preprocess_fps=round(float(payload["fps"]), 2),
        note="Measures OpenCV input preprocessing only; this is not detector inference FPS.",
    )


def run_detector_benchmark(
    project_root: Path,
    decision: VisionRuntimeDecision,
    *,
    model_path: Path | None = None,
) -> BenchmarkMetrics:
    """Run the production detector and report the provider that actually executed it."""

    python = project_python(project_root)
    if python is None:
        return BenchmarkMetrics(
            available=False,
            note="Project virtual environment was not found.",
        )
    if model_path is None:
        # Keep hardware imports independent from perception package startup.
        from friday.app.perception.detection.model_registry import (
            get_detection_model_path,
        )

        model_path = get_detection_model_path()
    resolved_model = model_path.resolve()
    script = f"""
import json, time
try:
    import numpy as np
    from friday.app.perception.detection.onnx_detector import OnnxObjectDetector
    detector = OnnxObjectDetector(
        {json.dumps(str(resolved_model))},
        providers=tuple({json.dumps(list(decision.execution_providers))}),
        confidence=0.35,
    )
    frame = np.zeros((720, 1280, 3), dtype=np.uint8)
    warmups = 3
    iterations = 12
    for _ in range(warmups):
        detector.detect(frame)
    pipeline_ms = []
    inference_ms = []
    for _ in range(iterations):
        started = time.perf_counter()
        detector.detect(frame)
        pipeline_ms.append((time.perf_counter() - started) * 1000)
        inference_ms.append(detector.last_inference_ms)
    average_pipeline_ms = sum(pipeline_ms) / len(pipeline_ms)
    average_inference_ms = sum(inference_ms) / len(inference_ms)
    print(json.dumps({{
        'ok': True,
        'iterations': iterations,
        'warmups': warmups,
        'average_pipeline_ms': average_pipeline_ms,
        'pipeline_fps': 1000 / average_pipeline_ms,
        'average_inference_ms': average_inference_ms,
        'inference_fps': 1000 / average_inference_ms,
        'providers': list(detector.providers),
        'model_input_width': detector.input_size[0],
        'model_input_height': detector.input_size[1],
    }}))
except Exception as exc:
    print(json.dumps({{'ok': False, 'error': type(exc).__name__ + ': ' + str(exc)}}))
"""
    try:
        completed = subprocess.run(
            [str(python), "-c", script],
            cwd=str(project_root),
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        payload = json.loads(completed.stdout.strip().splitlines()[-1])
    except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError, IndexError) as exc:
        return BenchmarkMetrics(
            available=False,
            model_path=str(resolved_model),
            note=f"Detector benchmark failed: {type(exc).__name__}.",
        )
    if not payload.get("ok"):
        return BenchmarkMetrics(
            available=False,
            model_path=str(resolved_model),
            note=str(payload.get("error") or "Unknown detector error"),
        )
    return BenchmarkMetrics(
        available=True,
        iterations=int(payload["iterations"]),
        warmup_iterations=int(payload["warmups"]),
        average_inference_ms=round(float(payload["average_inference_ms"]), 3),
        inference_fps=round(float(payload["inference_fps"]), 2),
        average_pipeline_ms=round(float(payload["average_pipeline_ms"]), 3),
        pipeline_fps=round(float(payload["pipeline_fps"]), 2),
        active_providers=tuple(str(item) for item in payload.get("providers") or ()),
        model_path=str(resolved_model),
        model_input_width=int(payload["model_input_width"]),
        model_input_height=int(payload["model_input_height"]),
        note="Measures the production ONNX detector on a synthetic 720p frame.",
    )


def _fallback_if_accelerator_inactive(
    decision: VisionRuntimeDecision,
    metrics: BenchmarkMetrics,
) -> VisionRuntimeDecision:
    primary_provider = decision.execution_providers[0]
    if decision.backend == "cpu" or not metrics.available:
        return decision
    if primary_provider in metrics.active_providers:
        return decision
    fallback = replace(
        decision,
        backend="cpu",
        execution_providers=("CPUExecutionProvider",),
        profile="cpu_safe",
        detector_model="yolo26n-onnx",
        input_size=320,
        detector_fps=3,
        tracker_fps=15,
        reasons=(
            *decision.reasons,
            f"{primary_provider} was advertised but did not initialize for the production model.",
            "Selected CPU compatibility mode after the live provider check.",
        ),
        warnings=(
            *decision.warnings,
            f"Vision accelerator validation failed; active providers were {metrics.active_providers or ('none',)}.",
        ),
    )
    return fallback


def create_benchmark_report(project_root: str | Path | None = None) -> VisionBenchmarkReport:
    root = find_project_root(project_root)
    hardware = probe_hardware(root)
    decision = decide_vision_runtime(hardware)
    metrics = run_detector_benchmark(root, decision)
    resolved_decision = _fallback_if_accelerator_inactive(decision, metrics)
    if resolved_decision is not decision:
        decision = resolved_decision
        metrics = run_detector_benchmark(root, decision)
    return VisionBenchmarkReport(
        generated_at=datetime.now(UTC).isoformat(),
        project_root=str(root),
        hardware=hardware,
        decision=decision,
        metrics=metrics,
    )
