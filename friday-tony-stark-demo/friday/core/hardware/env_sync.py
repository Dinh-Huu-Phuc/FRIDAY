from __future__ import annotations

import os
import tempfile
from pathlib import Path

from friday.core.hardware.schemas import VisionRuntimeDecision


def decision_env_values(decision: VisionRuntimeDecision) -> dict[str, str]:
    return {
        "FRIDAY_VISION_RESOLVED_BACKEND": decision.backend,
        "FRIDAY_VISION_RESOLVED_PROFILE": decision.profile,
        "FRIDAY_VISION_RESOLVED_MODEL": decision.detector_model,
        "FRIDAY_VISION_EXECUTION_PROVIDERS": ",".join(decision.execution_providers),
        "FRIDAY_VISION_INPUT_SIZE": str(decision.input_size),
        "FRIDAY_VISION_DETECTOR_FPS": str(decision.detector_fps),
        "FRIDAY_VISION_TRACKER_FPS": str(decision.tracker_fps),
        "FRIDAY_OLLAMA_PRELOAD": "true" if decision.ollama_preload else "false",
    }


def apply_decision_to_env(env_path: str | Path, decision: VisionRuntimeDecision) -> tuple[str, ...]:
    path = Path(env_path)
    values = decision_env_values(decision)
    original = path.read_text(encoding="utf-8") if path.is_file() else ""
    lines = original.splitlines()
    replaced: set[str] = set()
    output: list[str] = []
    for line in lines:
        stripped = line.lstrip()
        key = stripped.split("=", 1)[0].strip() if "=" in stripped else ""
        if key in values and not stripped.startswith("#"):
            output.append(f"{key}={values[key]}")
            replaced.add(key)
        else:
            output.append(line)
    if output and output[-1].strip():
        output.append("")
    for key, value in values.items():
        if key not in replaced:
            output.append(f"{key}={value}")

    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=str(path.parent),
        text=True,
    )
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as stream:
            stream.write("\n".join(output).rstrip() + "\n")
        os.replace(temporary_name, path)
    finally:
        if os.path.exists(temporary_name):
            os.unlink(temporary_name)
    return tuple(values)
