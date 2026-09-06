from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from friday.app.perception.licensing.schemas import VisionLicensePolicy


@dataclass(frozen=True, slots=True)
class VisionLicenseConfig:
    project_root: Path
    project_license_path: Path
    report_dir: Path
    policy: VisionLicensePolicy
    production_model: str
    enterprise_evidence_path: Path | None
    stale_after_days: int

    @classmethod
    def from_environment(cls) -> VisionLicenseConfig:
        project_root = Path(__file__).resolve().parents[4]
        repository_root = _find_repository_root(project_root)
        policy = _environment_policy()
        production_model = (
            (os.getenv("FRIDAY_VISION_PRODUCTION_MODEL") or "").strip().casefold()
        )
        if not production_model:
            production_model = _infer_model_key(
                os.getenv("FRIDAY_VISION_MODEL_PATH") or "yolo26n.onnx"
            )
        evidence = (
            os.getenv("FRIDAY_ULTRALYTICS_ENTERPRISE_LICENSE_PATH") or ""
        ).strip()
        report_value = (os.getenv("FRIDAY_VISION_LICENSE_REPORT_DIR") or "").strip()
        report_dir = (
            Path(report_value).expanduser()
            if report_value
            else project_root / "Benchmark" / "reports"
        )
        return cls(
            project_root=project_root,
            project_license_path=repository_root / "LICENSE",
            report_dir=report_dir.resolve(),
            policy=policy,
            production_model=production_model,
            enterprise_evidence_path=(
                Path(evidence).expanduser().resolve() if evidence else None
            ),
            stale_after_days=_environment_int(
                "FRIDAY_VISION_LICENSE_MAX_AGE_DAYS",
                default=180,
                minimum=30,
                maximum=730,
            ),
        )


def _environment_policy() -> VisionLicensePolicy:
    value = (
        (
            os.getenv("FRIDAY_VISION_LICENSE_POLICY")
            or VisionLicensePolicy.PERSONAL_RESEARCH.value
        )
        .strip()
        .casefold()
    )
    try:
        return VisionLicensePolicy(value)
    except ValueError:
        return VisionLicensePolicy.PERSONAL_RESEARCH


def _infer_model_key(model_path: str) -> str:
    filename = Path(model_path).name.casefold().replace("-", "_")
    if "rtdetrv4" in filename or "rt_detrv4" in filename:
        return "rtdetrv4_s"
    if "rfdetr" in filename or "rf_detr" in filename:
        if "2xl" in filename:
            return "rfdetr_2xlarge"
        if "xlarge" in filename or "_xl" in filename:
            return "rfdetr_xlarge"
        return "rfdetr_nano"
    if "yolo" in filename:
        return "yolo26n"
    return Path(model_path).stem.casefold()


def _environment_int(name: str, default: int, minimum: int, maximum: int) -> int:
    try:
        value = int((os.getenv(name) or str(default)).strip())
    except ValueError:
        return default
    return min(maximum, max(minimum, value))


def _find_repository_root(start: Path) -> Path:
    for candidate in (start, *start.parents):
        if (candidate / ".git").exists():
            return candidate
    return start
