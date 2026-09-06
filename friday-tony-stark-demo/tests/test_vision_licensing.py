from __future__ import annotations

import json
from pathlib import Path

from friday.app.perception.licensing import (
    AuditStatus,
    LicenseDecisionStatus,
    VisionLicenseAuditService,
    VisionLicenseConfig,
    VisionLicensePolicy,
    evaluate_model_license,
)


def test_yolo_is_research_only_and_blocked_for_mit_distribution() -> None:
    research = evaluate_model_license(
        "yolo26n",
        policy=VisionLicensePolicy.PERSONAL_RESEARCH,
    )
    distribution = evaluate_model_license(
        "yolo26n",
        policy=VisionLicensePolicy.MIT_DISTRIBUTION,
    )

    assert research.status == LicenseDecisionStatus.RESEARCH_ONLY
    assert research.compatible is True
    assert distribution.status == LicenseDecisionStatus.BLOCKED
    assert distribution.compatible is False


def test_apache_detector_is_compatible_with_mit_distribution() -> None:
    decision = evaluate_model_license(
        "rfdetr_nano",
        policy=VisionLicensePolicy.MIT_DISTRIBUTION,
    )

    assert decision.status == LicenseDecisionStatus.ALLOWED_WITH_NOTICE
    assert decision.compatible is True
    assert decision.license_id == "Apache-2.0"


def test_sam2_is_cataloged_as_optional_apache_component() -> None:
    decision = evaluate_model_license(
        "sam2_1_hiera_tiny",
        policy=VisionLicensePolicy.MIT_DISTRIBUTION,
    )

    assert decision.status == LicenseDecisionStatus.ALLOWED_WITH_NOTICE
    assert decision.compatible is True
    assert decision.license_id == "Apache-2.0"


def test_rfdetr_plus_variant_requires_manual_license_review() -> None:
    decision = evaluate_model_license(
        "rfdetr_xlarge",
        policy=VisionLicensePolicy.PROPRIETARY_DISTRIBUTION,
    )

    assert decision.status == LicenseDecisionStatus.BLOCKED
    assert decision.license_id == "PML-1.0"


def test_local_enterprise_evidence_allows_yolo_but_does_not_validate_terms(
    tmp_path: Path,
) -> None:
    evidence = tmp_path / "enterprise-license.txt"
    evidence.write_text("private agreement reference", encoding="utf-8")

    decision = evaluate_model_license(
        "yolo26n",
        policy=VisionLicensePolicy.PROPRIETARY_DISTRIBUTION,
        enterprise_evidence_path=evidence,
    )

    assert decision.compatible is True
    assert decision.status == LicenseDecisionStatus.ALLOWED_WITH_NOTICE
    assert "does not validate" in decision.reason


def test_release_audit_requires_project_license_file(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text(
        "# FRIDAY\n\n## License\n\nMIT\n", encoding="utf-8"
    )
    config = _config(tmp_path, production_model="rfdetr_nano")

    report = VisionLicenseAuditService(config).run()

    assert report.status == AuditStatus.BLOCKED
    assert report.release_ready is False
    assert report.project_license_file_present is False


def test_release_audit_rejects_invalid_project_license_file(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text(
        "# FRIDAY\n\n## License\n\nMIT\n",
        encoding="utf-8",
    )
    (tmp_path / "LICENSE").write_text("MIT\n", encoding="utf-8")

    report = VisionLicenseAuditService(
        _config(tmp_path, production_model="rfdetr_nano")
    ).run()

    assert report.status == AuditStatus.BLOCKED
    assert report.project_license_file_present is True
    assert report.project_license_file_valid is False


def test_release_audit_and_reports_pass_for_apache_model(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text(
        "# FRIDAY\n\n## License\n\nMIT\n", encoding="utf-8"
    )
    (tmp_path / "LICENSE").write_text(
        'MIT License\nPermission is hereby granted.\nTHE SOFTWARE IS PROVIDED "AS IS".\n',
        encoding="utf-8",
    )
    service = VisionLicenseAuditService(
        _config(tmp_path, production_model="rtdetrv4_s")
    )

    report = service.run()
    json_path, markdown_path = service.write_reports(report)

    assert report.status == AuditStatus.PASSED
    assert report.release_ready is True
    assert report.project_license_file_valid is True
    assert json.loads(json_path.read_text(encoding="utf-8"))["production_model"] == (
        "rtdetrv4_s"
    )
    assert "RT-DETRv4-S" in markdown_path.read_text(encoding="utf-8")


def _config(tmp_path: Path, *, production_model: str) -> VisionLicenseConfig:
    return VisionLicenseConfig(
        project_root=tmp_path,
        project_license_path=tmp_path / "LICENSE",
        report_dir=tmp_path / "reports",
        policy=VisionLicensePolicy.MIT_DISTRIBUTION,
        production_model=production_model,
        enterprise_evidence_path=None,
        stale_after_days=730,
    )
