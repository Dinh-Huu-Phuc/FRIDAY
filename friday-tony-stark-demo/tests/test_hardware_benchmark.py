from __future__ import annotations

from pathlib import Path

from friday.core.hardware import (
    BenchmarkMetrics,
    GpuDevice,
    HardwareSnapshot,
    apply_decision_to_env,
    decide_vision_runtime,
)
from friday.core.hardware import benchmark as benchmark_module


def _snapshot(*providers: str, memory_mb: int = 4096) -> HardwareSnapshot:
    return HardwareSnapshot(
        operating_system="Windows",
        cpu_name="Test CPU",
        logical_cpu_count=8,
        system_memory_mb=16384,
        gpus=(GpuDevice(name="Test NVIDIA GPU", total_memory_mb=memory_mb),),
        onnx_runtime_version="1.24.4",
        onnx_providers=providers,
    )


def test_gpu_without_cuda_provider_falls_back_to_cpu_safe() -> None:
    decision = decide_vision_runtime(
        _snapshot("AzureExecutionProvider", "CPUExecutionProvider")
    )

    assert decision.backend == "cpu"
    assert decision.profile == "cpu_safe"
    assert decision.input_size == 320
    assert decision.ollama_preload is False
    assert any("no CUDA/TensorRT" in warning for warning in decision.warnings)


def test_cuda_provider_uses_low_vram_profile_and_cpu_fallback() -> None:
    decision = decide_vision_runtime(
        _snapshot("CUDAExecutionProvider", "CPUExecutionProvider")
    )

    assert decision.backend == "cuda"
    assert decision.profile == "low_vram"
    assert decision.execution_providers == (
        "CUDAExecutionProvider",
        "CPUExecutionProvider",
    )


def test_auto_mode_prefers_cuda_when_tensorrt_is_only_advertised() -> None:
    decision = decide_vision_runtime(
        _snapshot(
            "TensorrtExecutionProvider",
            "CUDAExecutionProvider",
            "CPUExecutionProvider",
        )
    )

    assert decision.backend == "cuda"
    assert decision.execution_providers[0] == "CUDAExecutionProvider"


def test_higher_memory_gpu_selects_balanced_profile() -> None:
    decision = decide_vision_runtime(
        _snapshot("DmlExecutionProvider", "CPUExecutionProvider", memory_mb=8192)
    )

    assert decision.backend == "directml"
    assert decision.profile == "balanced"
    assert decision.input_size == 320
    assert decision.detector_model == "yolo26n-onnx"


def test_env_sync_preserves_existing_values_and_updates_only_runtime_keys(
    tmp_path: Path,
) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text(
        "DATABASE_URL=keep-me\nFRIDAY_OLLAMA_PRELOAD=true\n",
        encoding="utf-8",
    )
    decision = decide_vision_runtime(_snapshot("CPUExecutionProvider"))

    keys = apply_decision_to_env(env_path, decision)
    content = env_path.read_text(encoding="utf-8")

    assert "DATABASE_URL=keep-me" in content
    assert "FRIDAY_OLLAMA_PRELOAD=false" in content
    assert "FRIDAY_VISION_RESOLVED_BACKEND=cpu" in content
    assert len(keys) == 8


def test_benchmark_falls_back_when_advertised_cuda_provider_is_inactive(
    monkeypatch,
    tmp_path: Path,
) -> None:
    snapshot = _snapshot("CUDAExecutionProvider", "CPUExecutionProvider")
    accelerator_metrics = BenchmarkMetrics(
        available=True,
        active_providers=("CPUExecutionProvider",),
    )
    cpu_metrics = BenchmarkMetrics(
        available=True,
        active_providers=("CPUExecutionProvider",),
        average_inference_ms=40.0,
        inference_fps=25.0,
    )
    calls: list[str] = []

    monkeypatch.setattr(benchmark_module, "find_project_root", lambda root: tmp_path)
    monkeypatch.setattr(benchmark_module, "probe_hardware", lambda root: snapshot)

    def fake_detector_benchmark(root, decision):
        calls.append(decision.backend)
        return accelerator_metrics if decision.backend == "cuda" else cpu_metrics

    monkeypatch.setattr(
        benchmark_module,
        "run_detector_benchmark",
        fake_detector_benchmark,
    )

    report = benchmark_module.create_benchmark_report(tmp_path)

    assert calls == ["cuda", "cpu"]
    assert report.decision.backend == "cpu"
    assert report.decision.profile == "cpu_safe"
    assert report.metrics is cpu_metrics
    assert any("validation failed" in warning for warning in report.decision.warnings)
