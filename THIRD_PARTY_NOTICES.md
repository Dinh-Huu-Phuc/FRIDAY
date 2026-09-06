# Third-Party Vision Model Notices

FRIDAY's MIT license applies only to code owned by this repository. External
libraries, model architectures, downloaded checkpoints, exported weights, and
datasets remain governed by their respective licenses and terms.

This file is an engineering inventory, not legal advice. Verify the exact
artifact before distributing FRIDAY.

## Detector Candidates

| Component | Cataloged license | FRIDAY policy |
|---|---|---|
| Ultralytics YOLO26n code and trained models | AGPL-3.0 by default, or separately granted Enterprise terms | Local personal research only unless compatible rights are documented |
| RF-DETR Nano through Large core models | Apache-2.0 | Eligible for MIT/proprietary evaluation with required notices |
| RF-DETR XLarge and 2XLarge detection models | PML-1.0 | Blocked pending explicit manual review |
| RT-DETRv4-S official implementation | Apache-2.0 | Eligible for MIT/proprietary evaluation with required notices |
| Meta SAM 2.1 code and model checkpoints | Apache-2.0 | Optional, on-demand segmentation with required notices |

## Authoritative Sources

- Ultralytics licensing: https://www.ultralytics.com/license
- RF-DETR repository and model license matrix: https://github.com/roboflow/rf-detr
- RF-DETR Plus license: https://github.com/roboflow/rf-detr_plus/blob/main/LICENSE
- RT-DETRv4 license: https://github.com/RT-DETRs/RT-DETRv4/blob/main/LICENSE
- SAM 2 license: https://github.com/facebookresearch/sam2/blob/main/LICENSE

## Distribution Checklist

- Preserve the FRIDAY MIT `LICENSE` file.
- Include applicable Apache-2.0 license and NOTICE material with distributed
  RF-DETR core or RT-DETRv4 components.
- Do not assume an ONNX export changes the license of its source model.
- Do not commit private commercial agreements or license credentials.
- Re-run `friday-vision-license-audit` before publishing a build.
