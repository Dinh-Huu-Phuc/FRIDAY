from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class AnnotationConfig:
    root: Path
    max_labels: int = 20

    @classmethod
    def from_environment(cls) -> AnnotationConfig:
        default_root = Path(__file__).resolve().parents[3] / "trainModel" / "vision"
        configured_root = (os.getenv("FRIDAY_VISION_ANNOTATION_ROOT") or "").strip()
        root = Path(configured_root).expanduser() if configured_root else default_root
        return cls(
            root=root.resolve(),
            max_labels=_environment_int(
                "FRIDAY_VISION_ANNOTATION_MAX_LABELS",
                default=20,
                minimum=1,
                maximum=100,
            ),
        )


def _environment_int(name: str, default: int, minimum: int, maximum: int) -> int:
    try:
        value = int((os.getenv(name) or str(default)).strip())
    except ValueError:
        return default
    return min(maximum, max(minimum, value))
