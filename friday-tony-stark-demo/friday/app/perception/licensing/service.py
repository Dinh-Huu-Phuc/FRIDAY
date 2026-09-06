from __future__ import annotations

import os
import re
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from friday.app.perception.licensing.catalog import MODEL_LICENSE_CATALOG
from friday.app.perception.licensing.config import VisionLicenseConfig
from friday.app.perception.licensing.policy import evaluate_model_license
from friday.app.perception.licensing.schemas import (
    AuditStatus,
    LicenseDecisionStatus,
    VisionLicenseAuditReport,
    VisionLicensePolicy,
)


class VisionLicenseAuditService:
    def __init__(self, config: VisionLicenseConfig | None = None) -> None:
        self.config = config or VisionLicenseConfig.from_environment()

    def run(self) -> VisionLicenseAuditReport:
        decisions = tuple(
            evaluate_model_license(
                record.model_key,
                policy=self.config.policy,
                enterprise_evidence_path=self.config.enterprise_evidence_path,
            )
            for record in MODEL_LICENSE_CATALOG
        )
        selected = next(
            (
                decision
                for decision in decisions
                if decision.model_key == self.config.production_model
            ),
            evaluate_model_license(
                self.config.production_model,
                policy=self.config.policy,
                enterprise_evidence_path=self.config.enterprise_evidence_path,
            ),
        )
        declared_license = _read_declared_license(
            self.config.project_license_path.parent / "README.md"
        )
        license_file_present = self.config.project_license_path.is_file()
        license_file_valid = _is_mit_license_file(self.config.project_license_path)
        warnings = self._warnings(
            selected_status=selected.status,
            declared_license=declared_license,
            license_file_present=license_file_present,
            license_file_valid=license_file_valid,
        )
        distribution_policy = self.config.policy in {
            VisionLicensePolicy.MIT_DISTRIBUTION,
            VisionLicensePolicy.PROPRIETARY_DISTRIBUTION,
        }
        project_license_ready = (
            license_file_present and license_file_valid and declared_license == "MIT"
        )
        blocked = not selected.compatible or (
            distribution_policy and not project_license_ready
        )
        if blocked:
            status = AuditStatus.BLOCKED
        elif warnings or selected.status == LicenseDecisionStatus.RESEARCH_ONLY:
            status = AuditStatus.WARNING
        else:
            status = AuditStatus.PASSED
        release_ready = distribution_policy and status == AuditStatus.PASSED
        return VisionLicenseAuditReport(
            generated_at=datetime.now(UTC).isoformat(),
            policy=self.config.policy,
            production_model=self.config.production_model,
            project_declared_license=declared_license,
            project_license_file=str(self.config.project_license_path),
            project_license_file_present=license_file_present,
            project_license_file_valid=license_file_valid,
            enterprise_evidence_path=(
                str(self.config.enterprise_evidence_path)
                if self.config.enterprise_evidence_path
                else ""
            ),
            decisions=decisions,
            selected_decision=selected,
            status=status,
            release_ready=release_ready,
            warnings=tuple(warnings),
        )

    def write_reports(self, report: VisionLicenseAuditReport) -> tuple[Path, Path]:
        self.config.report_dir.mkdir(parents=True, exist_ok=True)
        json_path = self.config.report_dir / "friday_vision_license_audit_latest.json"
        markdown_path = self.config.report_dir / "friday_vision_license_audit_latest.md"
        _atomic_write(json_path, report.model_dump_json(indent=2) + "\n")
        _atomic_write(markdown_path, _markdown_report(report))
        return json_path, markdown_path

    def _warnings(
        self,
        *,
        selected_status: LicenseDecisionStatus,
        declared_license: str,
        license_file_present: bool,
        license_file_valid: bool,
    ) -> list[str]:
        warnings: list[str] = []
        if not license_file_present:
            warnings.append("The project declares MIT but has no root LICENSE file.")
        elif not license_file_valid:
            warnings.append(
                "The root LICENSE file does not contain the expected MIT license terms."
            )
        if declared_license != "MIT":
            warnings.append(
                "The root README does not contain an unambiguous MIT license declaration."
            )
        if self.config.policy == VisionLicensePolicy.PERSONAL_RESEARCH:
            warnings.append(
                "Personal-research mode is not a distribution or production-release approval."
            )
        if (
            self.config.enterprise_evidence_path is not None
            and not self.config.enterprise_evidence_path.is_file()
        ):
            warnings.append(
                "The configured Ultralytics Enterprise evidence file does not exist."
            )
        cutoff = datetime.now(UTC).date().toordinal() - self.config.stale_after_days
        stale_records = [
            record.display_name
            for record in MODEL_LICENSE_CATALOG
            if record.verified_on.toordinal() < cutoff
        ]
        if stale_records:
            warnings.append(
                "Re-verify stale model-license records: " + ", ".join(stale_records)
            )
        if selected_status == LicenseDecisionStatus.RESEARCH_ONLY:
            warnings.append(
                "The selected model is approved only for FRIDAY's local research policy."
            )
        return warnings


def _read_declared_license(readme_path: Path) -> str:
    if not readme_path.is_file():
        return "UNKNOWN"
    content = readme_path.read_text(encoding="utf-8", errors="replace")
    match = re.search(
        r"^##\s+License\s*$\s*^\s*([^\r\n]+)",
        content,
        flags=re.IGNORECASE | re.MULTILINE,
    )
    if not match:
        return "UNKNOWN"
    declared = match.group(1).strip()
    return "MIT" if declared.casefold() == "mit" else declared[:100]


def _is_mit_license_file(license_path: Path) -> bool:
    if not license_path.is_file():
        return False
    content = license_path.read_text(encoding="utf-8", errors="replace").casefold()
    required_phrases = (
        "mit license",
        "permission is hereby granted",
        'the software is provided "as is"',
    )
    return all(phrase in content for phrase in required_phrases)


def _atomic_write(path: Path, content: str) -> None:
    temporary = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    try:
        temporary.write_text(content, encoding="utf-8")
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _markdown_report(report: VisionLicenseAuditReport) -> str:
    lines = [
        "# FRIDAY Vision License Audit",
        "",
        f"- Generated: `{report.generated_at}`",
        f"- Policy: `{report.policy.value}`",
        f"- Selected model: `{report.production_model}`",
        f"- Audit status: `{report.status.value}`",
        f"- Release ready: `{str(report.release_ready).lower()}`",
        f"- Project license: `{report.project_declared_license}`",
        f"- Root LICENSE present: `{str(report.project_license_file_present).lower()}`",
        f"- Root LICENSE valid: `{str(report.project_license_file_valid).lower()}`",
        "",
        "| Model | License | Decision | Compatible | Verified |",
        "| --- | --- | --- | --- | --- |",
    ]
    for decision in report.decisions:
        lines.append(
            f"| {decision.display_name} | {decision.license_id} | "
            f"{decision.status.value} | {str(decision.compatible).lower()} | "
            f"{decision.verified_on or '-'} |"
        )
    lines.extend(("", "## Selected Model", "", report.selected_decision.reason))
    if report.selected_decision.obligations:
        lines.extend(("", "### Required Actions", ""))
        lines.extend(
            f"- {obligation}" for obligation in report.selected_decision.obligations
        )
    if report.warnings:
        lines.extend(("", "## Warnings", ""))
        lines.extend(f"- {warning}" for warning in report.warnings)
    lines.extend(("", f"> {report.disclaimer}", ""))
    return "\n".join(lines)
