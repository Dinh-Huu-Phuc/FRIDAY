from __future__ import annotations

import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from friday.core.hardware.policy import decide_vision_runtime
from friday.core.hardware.probe import find_project_root, probe_hardware, project_python
from friday.core.hardware.schemas import BenchmarkMetrics, VisionBenchmarkReport


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


def create_benchmark_report(project_root: str | Path | None = None) -> VisionBenchmarkReport:
    root = find_project_root(project_root)
    hardware = probe_hardware(root)
    decision = decide_vision_runtime(hardware)
    metrics = run_preprocess_benchmark(root, decision.input_size)
    return VisionBenchmarkReport(
        generated_at=datetime.now(UTC).isoformat(),
        project_root=str(root),
        hardware=hardware,
        decision=decision,
        metrics=metrics,
    )
