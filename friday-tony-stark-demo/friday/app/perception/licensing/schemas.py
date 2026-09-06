from __future__ import annotations

from datetime import date
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class VisionLicensePolicy(str, Enum):
    PERSONAL_RESEARCH = "personal_research"
    MIT_DISTRIBUTION = "mit_distribution"
    PROPRIETARY_DISTRIBUTION = "proprietary_distribution"


class LicenseKind(str, Enum):
    PERMISSIVE = "permissive"
    STRONG_COPYLEFT = "strong_copyleft"
    COMMERCIAL = "commercial"
    RESTRICTED = "restricted"


class LicenseDecisionStatus(str, Enum):
    ALLOWED = "allowed"
    ALLOWED_WITH_NOTICE = "allowed_with_notice"
    RESEARCH_ONLY = "research_only"
    BLOCKED = "blocked"
    UNVERIFIED = "unverified"


class AuditStatus(str, Enum):
    PASSED = "passed"
    WARNING = "warning"
    BLOCKED = "blocked"


class ModelLicenseRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    model_key: str
    display_name: str
    family: str
    license_id: str
    license_kind: LicenseKind
    source_url: str
    verified_on: date
    notice: str


class ModelLicenseDecision(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    model_key: str
    display_name: str
    policy: VisionLicensePolicy
    license_id: str
    effective_license: str
    status: LicenseDecisionStatus
    compatible: bool
    source_url: str
    verified_on: date | None = None
    reason: str
    obligations: tuple[str, ...] = ()


class VisionLicenseAuditReport(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: int = 1
    generated_at: str
    policy: VisionLicensePolicy
    production_model: str
    project_declared_license: str
    project_license_file: str
    project_license_file_present: bool
    project_license_file_valid: bool
    enterprise_evidence_path: str = ""
    decisions: tuple[ModelLicenseDecision, ...]
    selected_decision: ModelLicenseDecision
    status: AuditStatus
    release_ready: bool
    warnings: tuple[str, ...] = ()
    disclaimer: str = Field(
        default=(
            "This automated inventory is an engineering safeguard, not legal advice. "
            "Verify the exact code, weights, and commercial agreements before distribution."
        )
    )
