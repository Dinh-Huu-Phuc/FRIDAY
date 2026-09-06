from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from friday.app.perception.evaluation.schemas import (
    BenchmarkBox,
    EvaluationDataset,
    EvaluationSample,
    GroundTruth,
)


class EvaluationDatasetError(RuntimeError):
    """Raised when a reviewed COCO dataset cannot be used for comparison."""


def load_coco_dataset(
    manifest_path: str | Path,
    *,
    dataset_root: str | Path,
    role: str,
    max_images: int = 0,
) -> EvaluationDataset:
    manifest = Path(manifest_path).expanduser().resolve()
    root = Path(dataset_root).expanduser().resolve()
    if not manifest.is_file():
        raise EvaluationDatasetError(f"COCO manifest was not found: {manifest}")
    if max_images < 0:
        raise EvaluationDatasetError("max_images cannot be negative.")

    try:
        payload = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise EvaluationDatasetError(f"Could not read COCO manifest: {exc}") from exc
    if not isinstance(payload, dict):
        raise EvaluationDatasetError("The COCO manifest must contain a JSON object.")

    categories = _load_categories(payload.get("categories"))
    annotations_by_image = _load_annotations(payload.get("annotations"), categories)
    raw_images = payload.get("images")
    if not isinstance(raw_images, list) or not raw_images:
        raise EvaluationDatasetError("The COCO manifest does not contain any images.")

    samples: list[EvaluationSample] = []
    fingerprint_rows: list[dict[str, Any]] = []
    for raw_image in sorted(raw_images, key=lambda item: int(item.get("id", 0))):
        if max_images and len(samples) >= max_images:
            break
        sample, fingerprint_row = _load_sample(raw_image, annotations_by_image, root)
        samples.append(sample)
        fingerprint_rows.append(fingerprint_row)

    total_boxes = sum(len(sample.ground_truth) for sample in samples)
    if total_boxes == 0:
        raise EvaluationDatasetError(
            "The selected COCO images have no reviewed ground-truth boxes."
        )

    warnings: list[str] = []
    normalized_role = role.strip().lower()
    if normalized_role not in {"validation", "test"}:
        warnings.append(
            "Dataset role is not validation/test; results are diagnostic and cannot "
            "select a production model."
        )
    digest = hashlib.sha256()
    digest.update(
        json.dumps(
            {
                "categories": categories,
                "samples": fingerprint_rows,
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    )
    for sample in samples:
        digest.update(sample.file_path.read_bytes())

    return EvaluationDataset(
        root=root,
        manifest_path=manifest,
        role=normalized_role,
        samples=tuple(samples),
        class_names=tuple(categories[key] for key in sorted(categories)),
        fingerprint=digest.hexdigest(),
        total_boxes=total_boxes,
        warnings=tuple(warnings),
    )


def _load_categories(raw_categories: Any) -> dict[int, str]:
    if not isinstance(raw_categories, list) or not raw_categories:
        raise EvaluationDatasetError("The COCO manifest has no categories.")
    categories: dict[int, str] = {}
    names: set[str] = set()
    for item in raw_categories:
        try:
            category_id = int(item["id"])
            name = " ".join(str(item["name"]).strip().split()).casefold()
        except (KeyError, TypeError, ValueError) as exc:
            raise EvaluationDatasetError(f"Invalid COCO category: {item!r}") from exc
        if category_id in categories or name in names or not name:
            raise EvaluationDatasetError(
                f"Invalid or duplicate COCO category: {item!r}"
            )
        categories[category_id] = name
        names.add(name)
    return categories


def _load_annotations(
    raw_annotations: Any,
    categories: dict[int, str],
) -> dict[int, list[GroundTruth]]:
    if not isinstance(raw_annotations, list):
        raise EvaluationDatasetError("The COCO annotations field must be an array.")
    annotations: dict[int, list[GroundTruth]] = defaultdict(list)
    for item in raw_annotations:
        try:
            image_id = int(item["image_id"])
            category_id = int(item["category_id"])
            x, y, width, height = (float(value) for value in item["bbox"])
        except (KeyError, TypeError, ValueError) as exc:
            raise EvaluationDatasetError(f"Invalid COCO annotation: {item!r}") from exc
        if category_id not in categories:
            raise EvaluationDatasetError(
                f"Annotation references unknown category {category_id}."
            )
        if x < 0.0 or y < 0.0 or width <= 0.0 or height <= 0.0:
            raise EvaluationDatasetError(f"Invalid COCO bbox: {item.get('bbox')!r}")
        annotations[image_id].append(
            GroundTruth(
                label=categories[category_id],
                box=BenchmarkBox(x1=x, y1=y, x2=x + width, y2=y + height),
            )
        )
    return annotations


def _load_sample(
    raw_image: Any,
    annotations_by_image: dict[int, list[GroundTruth]],
    root: Path,
) -> tuple[EvaluationSample, dict[str, Any]]:
    try:
        image_id = int(raw_image["id"])
        relative_name = str(raw_image["file_name"])
        width = int(raw_image["width"])
        height = int(raw_image["height"])
    except (KeyError, TypeError, ValueError) as exc:
        raise EvaluationDatasetError(f"Invalid COCO image: {raw_image!r}") from exc
    if width <= 0 or height <= 0:
        raise EvaluationDatasetError(f"Image {image_id} has invalid dimensions.")
    file_path = (root / relative_name).resolve()
    try:
        file_path.relative_to(root)
    except ValueError as exc:
        raise EvaluationDatasetError(
            f"Image {image_id} escapes the configured dataset root."
        ) from exc
    if not file_path.is_file():
        raise EvaluationDatasetError(f"COCO image was not found: {file_path}")
    ground_truth = tuple(annotations_by_image.get(image_id, ()))
    for truth in ground_truth:
        if truth.box.x2 > width or truth.box.y2 > height:
            raise EvaluationDatasetError(
                f"Ground-truth box for image {image_id} exceeds image dimensions."
            )
    sample = EvaluationSample(
        image_id=image_id,
        file_path=file_path,
        width=width,
        height=height,
        ground_truth=ground_truth,
    )
    fingerprint_row = {
        "id": image_id,
        "file_name": relative_name.replace("\\", "/"),
        "width": width,
        "height": height,
        "ground_truth": [
            {
                "label": truth.label,
                "box": truth.box.model_dump(),
            }
            for truth in ground_truth
        ],
    }
    return sample, fingerprint_row
