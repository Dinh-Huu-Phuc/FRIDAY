from __future__ import annotations

from datetime import date

from friday.app.perception.licensing.schemas import (
    LicenseKind,
    ModelLicenseRecord,
)

_VERIFIED_ON = date(2026, 9, 5)

MODEL_LICENSE_CATALOG: tuple[ModelLicenseRecord, ...] = (
    ModelLicenseRecord(
        model_key="yolo26n",
        display_name="Ultralytics YOLO26n",
        family="Ultralytics YOLO26",
        license_id="AGPL-3.0",
        license_kind=LicenseKind.STRONG_COPYLEFT,
        source_url="https://www.ultralytics.com/license",
        verified_on=_VERIFIED_ON,
        notice=(
            "Ultralytics publishes its code and trained models under AGPL-3.0 by "
            "default and offers separate Enterprise terms."
        ),
    ),
    ModelLicenseRecord(
        model_key="rfdetr_nano",
        display_name="RF-DETR Nano",
        family="RF-DETR Core",
        license_id="Apache-2.0",
        license_kind=LicenseKind.PERMISSIVE,
        source_url="https://github.com/roboflow/rf-detr",
        verified_on=_VERIFIED_ON,
        notice=(
            "RF-DETR core code and Nano through Large model weights are designated "
            "Apache-2.0. XL and 2XL detection models are not covered by this entry."
        ),
    ),
    ModelLicenseRecord(
        model_key="rtdetrv4_s",
        display_name="RT-DETRv4-S",
        family="RT-DETRv4",
        license_id="Apache-2.0",
        license_kind=LicenseKind.PERMISSIVE,
        source_url="https://github.com/RT-DETRs/RT-DETRv4/blob/main/LICENSE",
        verified_on=_VERIFIED_ON,
        notice="The official RT-DETRv4 repository is distributed under Apache-2.0.",
    ),
    ModelLicenseRecord(
        model_key="sam2_1_hiera_tiny",
        display_name="SAM 2.1 Hiera Tiny",
        family="Meta Segment Anything 2",
        license_id="Apache-2.0",
        license_kind=LicenseKind.PERMISSIVE,
        source_url="https://github.com/facebookresearch/sam2/blob/main/LICENSE",
        verified_on=_VERIFIED_ON,
        notice=(
            "Meta publishes the official SAM 2 code and model checkpoints under "
            "Apache-2.0. Preserve its license and applicable notices when distributing."
        ),
    ),
    ModelLicenseRecord(
        model_key="rfdetr_xlarge",
        display_name="RF-DETR XLarge",
        family="RF-DETR Plus",
        license_id="PML-1.0",
        license_kind=LicenseKind.RESTRICTED,
        source_url="https://github.com/roboflow/rf-detr_plus/blob/main/LICENSE",
        verified_on=_VERIFIED_ON,
        notice=(
            "RF-DETR XLarge detection belongs to RF-DETR Plus and requires separate "
            "Platform Model License compliance."
        ),
    ),
    ModelLicenseRecord(
        model_key="rfdetr_2xlarge",
        display_name="RF-DETR 2XLarge",
        family="RF-DETR Plus",
        license_id="PML-1.0",
        license_kind=LicenseKind.RESTRICTED,
        source_url="https://github.com/roboflow/rf-detr_plus/blob/main/LICENSE",
        verified_on=_VERIFIED_ON,
        notice=(
            "RF-DETR 2XLarge detection belongs to RF-DETR Plus and requires separate "
            "Platform Model License compliance."
        ),
    ),
)

_CATALOG_BY_KEY = {record.model_key: record for record in MODEL_LICENSE_CATALOG}


def get_model_license_record(model_key: str) -> ModelLicenseRecord | None:
    return _CATALOG_BY_KEY.get(model_key.strip().casefold())
