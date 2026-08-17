from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class GpuDevice:
    name: str
    total_memory_mb: int | None = None
    free_memory_mb: int | None = None
    driver_version: str = ""
    compute_capability: str = ""


@dataclass(frozen=True, slots=True)
class HardwareSnapshot:
    operating_system: str
    cpu_name: str
    logical_cpu_count: int
    system_memory_mb: int | None
    gpus: tuple[GpuDevice, ...] = ()
    onnx_runtime_version: str = ""
    onnx_providers: tuple[str, ...] = ()
    probe_warnings: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class VisionRuntimeDecision:
    backend: str
    execution_providers: tuple[str, ...]
    profile: str
    detector_model: str
    input_size: int
    detector_fps: int
    tracker_fps: int
    ollama_preload: bool
    reasons: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class BenchmarkMetrics:
    available: bool
    iterations: int = 0
    average_preprocess_ms: float | None = None
    preprocess_fps: float | None = None
    note: str = ""


@dataclass(frozen=True, slots=True)
class VisionBenchmarkReport:
    generated_at: str
    project_root: str
    hardware: HardwareSnapshot
    decision: VisionRuntimeDecision
    metrics: BenchmarkMetrics
    applied_env_keys: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
