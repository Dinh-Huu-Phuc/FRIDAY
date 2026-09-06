from __future__ import annotations

import argparse
from dataclasses import replace
from pathlib import Path

from friday.app.perception.licensing.config import VisionLicenseConfig
from friday.app.perception.licensing.schemas import AuditStatus, VisionLicensePolicy
from friday.app.perception.licensing.service import VisionLicenseAuditService


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="friday-vision-license-audit",
        description="Audit FRIDAY's selected detector against a deployment policy.",
    )
    parser.add_argument(
        "--policy",
        choices=tuple(policy.value for policy in VisionLicensePolicy),
    )
    parser.add_argument("--production-model")
    parser.add_argument("--enterprise-license-evidence", type=Path)
    parser.add_argument("--report-dir", type=Path)
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Return a non-zero status unless the audit fully passes.",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    config = VisionLicenseConfig.from_environment()
    config = replace(
        config,
        policy=(VisionLicensePolicy(args.policy) if args.policy else config.policy),
        production_model=(
            args.production_model.strip().casefold()
            if args.production_model
            else config.production_model
        ),
        enterprise_evidence_path=(
            args.enterprise_license_evidence.resolve()
            if args.enterprise_license_evidence
            else config.enterprise_evidence_path
        ),
        report_dir=(
            args.report_dir.resolve() if args.report_dir else config.report_dir
        ),
    )
    service = VisionLicenseAuditService(config)
    report = service.run()
    json_path, markdown_path = service.write_reports(report)

    print(f"Policy: {report.policy.value}")
    print(f"Selected model: {report.production_model}")
    print(f"Decision: {report.selected_decision.status.value}")
    print(f"Audit status: {report.status.value}")
    print(f"Release ready: {str(report.release_ready).lower()}")
    print(f"JSON report: {json_path}")
    print(f"Markdown report: {markdown_path}")
    for warning in report.warnings:
        print(f"WARNING: {warning}")
    if args.strict and report.status != AuditStatus.PASSED:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
