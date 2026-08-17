from __future__ import annotations

import os

from friday.core.hardware.schemas import HardwareSnapshot, VisionRuntimeDecision

_BACKEND_PROVIDERS = {
    "tensorrt": "TensorrtExecutionProvider",
    "cuda": "CUDAExecutionProvider",
    "directml": "DmlExecutionProvider",
    "openvino": "OpenVINOExecutionProvider",
    "cpu": "CPUExecutionProvider",
}
_BACKEND_PRIORITY = ("tensorrt", "cuda", "directml", "openvino", "cpu")
_PROFILE_SETTINGS = {
    "cpu_safe": (320, 3, 15, "yolo26n-onnx"),
    "low_vram": (416, 7, 20, "yolo26n-onnx"),
    "balanced": (512, 10, 24, "rfdetr-nano-onnx"),
    "performance": (640, 15, 30, "rfdetr-small-onnx"),
}


def _select_backend(snapshot: HardwareSnapshot, requested: str) -> tuple[str, list[str]]:
    available = set(snapshot.onnx_providers)
    warnings: list[str] = []
    if requested and requested != "auto":
        provider = _BACKEND_PROVIDERS.get(requested)
        if provider and provider in available:
            return requested, warnings
        warnings.append(
            f"Requested backend '{requested}' is unavailable in the project environment; auto selection was used."
        )
    for backend in _BACKEND_PRIORITY:
        if _BACKEND_PROVIDERS[backend] in available:
            return backend, warnings
    warnings.append("No ONNX execution provider was detected; CPU compatibility mode was selected.")
    return "cpu", warnings


def _auto_profile(snapshot: HardwareSnapshot, backend: str) -> str:
    if backend == "cpu":
        return "cpu_safe"
    memory_values = [gpu.total_memory_mb for gpu in snapshot.gpus if gpu.total_memory_mb]
    if not memory_values:
        return "low_vram"
    memory_mb = max(memory_values)
    if memory_mb <= 4608:
        return "low_vram"
    if memory_mb <= 8192:
        return "balanced"
    return "performance"


def decide_vision_runtime(
    snapshot: HardwareSnapshot,
    *,
    requested_backend: str | None = None,
    requested_profile: str | None = None,
) -> VisionRuntimeDecision:
    backend_request = (
        requested_backend or os.getenv("FRIDAY_VISION_BACKEND", "auto")
    ).strip().lower()
    profile_request = (
        requested_profile or os.getenv("FRIDAY_VISION_PROFILE", "auto")
    ).strip().lower()
    backend, warnings = _select_backend(snapshot, backend_request)
    profile = _auto_profile(snapshot, backend)
    if profile_request != "auto":
        if profile_request in _PROFILE_SETTINGS:
            profile = profile_request
        else:
            warnings.append(
                f"Unknown profile '{profile_request}' was ignored; profile '{profile}' was selected."
            )

    input_size, detector_fps, tracker_fps, detector_model = _PROFILE_SETTINGS[profile]
    selected_provider = _BACKEND_PROVIDERS[backend]
    providers = [selected_provider]
    if selected_provider != "CPUExecutionProvider" and "CPUExecutionProvider" in snapshot.onnx_providers:
        providers.append("CPUExecutionProvider")

    reasons = [f"Selected {backend} because {selected_provider} is available."]
    if snapshot.gpus:
        gpu = max(snapshot.gpus, key=lambda item: item.total_memory_mb or 0)
        memory = f" with {gpu.total_memory_mb} MB VRAM" if gpu.total_memory_mb else ""
        reasons.append(f"Detected {gpu.name}{memory}.")
    if backend == "cpu" and snapshot.gpus:
        warnings.append(
            "An NVIDIA GPU is present, but the project ONNX Runtime has no CUDA/TensorRT provider. "
            "FRIDAY will remain on CPU until a compatible GPU provider is installed."
        )
    reasons.append(
        f"Profile '{profile}' uses {input_size}px detector input at a target of {detector_fps} FPS."
    )

    maximum_vram = max(
        (gpu.total_memory_mb or 0 for gpu in snapshot.gpus),
        default=0,
    )
    ollama_preload = not (0 < maximum_vram <= 4608)
    if not ollama_preload:
        reasons.append("Ollama preload is disabled to protect limited GPU memory.")

    return VisionRuntimeDecision(
        backend=backend,
        execution_providers=tuple(providers),
        profile=profile,
        detector_model=detector_model,
        input_size=input_size,
        detector_fps=detector_fps,
        tracker_fps=tracker_fps,
        ollama_preload=ollama_preload,
        reasons=tuple(reasons),
        warnings=(*snapshot.probe_warnings, *warnings),
    )
