from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

FRIDAY_DIR = Path(__file__).resolve().parents[3]


@dataclass(frozen=True, slots=True)
class Sam2Config:
    enabled: bool
    checkpoint_path: Path
    model_config: str
    device: str
    minimum_cuda_vram_mb: int
    multimask_output: bool
    tracking_fps: float
    tracking_max_misses: int
    result_ttl_seconds: float

    @classmethod
    def from_environment(cls) -> Sam2Config:
        checkpoint = (
            os.getenv("FRIDAY_SAM2_CHECKPOINT")
            or "assets/models/sam2/sam2.1_hiera_tiny.pt"
        ).strip()
        checkpoint_path = Path(checkpoint).expanduser()
        if not checkpoint_path.is_absolute():
            checkpoint_path = FRIDAY_DIR / checkpoint_path
        return cls(
            enabled=_environment_bool("FRIDAY_SAM2_ENABLED", True),
            checkpoint_path=checkpoint_path.resolve(),
            model_config=(
                os.getenv("FRIDAY_SAM2_MODEL_CONFIG")
                or "configs/sam2.1/sam2.1_hiera_t.yaml"
            ).strip(),
            device=(os.getenv("FRIDAY_SAM2_DEVICE") or "auto").strip().lower(),
            minimum_cuda_vram_mb=_environment_int(
                "FRIDAY_SAM2_MIN_CUDA_VRAM_MB", 3584, 1024, 65536
            ),
            multimask_output=_environment_bool("FRIDAY_SAM2_MULTIMASK", True),
            tracking_fps=_environment_float(
                "FRIDAY_SAM2_TRACKING_FPS", 1.0, 0.1, 5.0
            ),
            tracking_max_misses=_environment_int(
                "FRIDAY_SAM2_TRACKING_MAX_MISSES", 5, 1, 60
            ),
            result_ttl_seconds=_environment_float(
                "FRIDAY_SAM2_RESULT_TTL", 30.0, 1.0, 300.0
            ),
        )


def segmentation_result_ttl() -> float:
    return Sam2Config.from_environment().result_ttl_seconds


def _environment_bool(name: str, default: bool) -> bool:
    raw = (os.getenv(name) or ("true" if default else "false")).strip().lower()
    return raw in {"1", "true", "yes", "on"}


def _environment_float(
    name: str,
    default: float,
    minimum: float,
    maximum: float,
) -> float:
    try:
        value = float((os.getenv(name) or str(default)).strip())
    except ValueError:
        return default
    return min(maximum, max(minimum, value))

def _environment_int(name: str, default: int, minimum: int, maximum: int) -> int:
    try:
        value = int((os.getenv(name) or str(default)).strip())
    except ValueError:
        return default
    return min(maximum, max(minimum, value))
