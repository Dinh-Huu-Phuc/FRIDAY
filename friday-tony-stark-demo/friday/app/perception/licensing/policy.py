from __future__ import annotations

from pathlib import Path

from friday.app.perception.licensing.catalog import get_model_license_record
from friday.app.perception.licensing.schemas import (
    LicenseDecisionStatus,
    LicenseKind,
    ModelLicenseDecision,
    VisionLicensePolicy,
)


def evaluate_model_license(
    model_key: str,
    *,
    policy: VisionLicensePolicy,
    enterprise_evidence_path: Path | None = None,
) -> ModelLicenseDecision:
    record = get_model_license_record(model_key)
    if record is None:
        return ModelLicenseDecision(
            model_key=model_key,
            display_name=model_key,
            policy=policy,
            license_id="UNKNOWN",
            effective_license="UNKNOWN",
            status=LicenseDecisionStatus.UNVERIFIED,
            compatible=False,
            source_url="",
            reason="This model is not present in FRIDAY's verified license catalog.",
            obligations=("Verify the exact source-code and weight licenses manually.",),
        )

    enterprise_evidence_exists = bool(
        enterprise_evidence_path and enterprise_evidence_path.is_file()
    )
    if record.model_key == "yolo26n" and enterprise_evidence_exists:
        return ModelLicenseDecision(
            model_key=record.model_key,
            display_name=record.display_name,
            policy=policy,
            license_id=record.license_id,
            effective_license="Ultralytics Enterprise (locally attested)",
            status=LicenseDecisionStatus.ALLOWED_WITH_NOTICE,
            compatible=True,
            source_url=record.source_url,
            verified_on=record.verified_on,
            reason=(
                "A local Enterprise-license evidence file was supplied. The audit does "
                "not validate the agreement's scope or validity."
            ),
            obligations=(
                "Confirm that the agreement covers this project, model, deployment, and users.",
                "Keep the agreement outside source control.",
            ),
        )

    if record.license_kind == LicenseKind.PERMISSIVE:
        status = (
            LicenseDecisionStatus.ALLOWED
            if policy == VisionLicensePolicy.PERSONAL_RESEARCH
            else LicenseDecisionStatus.ALLOWED_WITH_NOTICE
        )
        obligations = ()
        if status == LicenseDecisionStatus.ALLOWED_WITH_NOTICE:
            obligations = (
                "Include a copy of the Apache-2.0 license when distributing the work.",
                "Retain applicable copyright, attribution, and NOTICE content.",
                "Mark modified upstream files when required.",
            )
        return ModelLicenseDecision(
            model_key=record.model_key,
            display_name=record.display_name,
            policy=policy,
            license_id=record.license_id,
            effective_license=record.license_id,
            status=status,
            compatible=True,
            source_url=record.source_url,
            verified_on=record.verified_on,
            reason=(
                f"{record.display_name} is cataloged as {record.license_id} and is "
                f"compatible with the {policy.value} engineering policy."
            ),
            obligations=obligations,
        )

    if (
        record.license_kind == LicenseKind.STRONG_COPYLEFT
        and policy == VisionLicensePolicy.PERSONAL_RESEARCH
    ):
        return ModelLicenseDecision(
            model_key=record.model_key,
            display_name=record.display_name,
            policy=policy,
            license_id=record.license_id,
            effective_license=record.license_id,
            status=LicenseDecisionStatus.RESEARCH_ONLY,
            compatible=True,
            source_url=record.source_url,
            verified_on=record.verified_on,
            reason=(
                "Allowed by FRIDAY's personal-research policy only. This decision must "
                "be re-audited before distribution or network deployment."
            ),
            obligations=(
                "Do not treat this result as approval for MIT or proprietary distribution.",
                "Review AGPL-3.0 obligations or obtain appropriate commercial terms before release.",
            ),
        )

    if record.license_kind == LicenseKind.RESTRICTED:
        reason = (
            f"{record.display_name} uses {record.license_id}; FRIDAY requires explicit "
            "manual approval and evidence for this license."
        )
    else:
        reason = (
            f"{record.display_name} defaults to {record.license_id}, which is not "
            f"compatible with FRIDAY's {policy.value} policy without separate rights."
        )
    return ModelLicenseDecision(
        model_key=record.model_key,
        display_name=record.display_name,
        policy=policy,
        license_id=record.license_id,
        effective_license=record.license_id,
        status=LicenseDecisionStatus.BLOCKED,
        compatible=False,
        source_url=record.source_url,
        verified_on=record.verified_on,
        reason=reason,
        obligations=(
            "Choose a compatible model or document separately granted rights.",
            "Have distribution terms reviewed by a qualified legal professional.",
        ),
    )
