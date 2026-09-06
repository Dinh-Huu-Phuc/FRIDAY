from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping

from friday.app.perception.evaluation.schemas import (
    BenchmarkBox,
    BenchmarkDetection,
    EvaluationDataset,
    MetricSummary,
    PerClassMetrics,
)


def evaluate_detections(
    dataset: EvaluationDataset,
    predictions: Mapping[int, tuple[BenchmarkDetection, ...]],
    *,
    operating_confidence: float,
    iou_thresholds: tuple[float, ...],
) -> MetricSummary:
    if not iou_thresholds:
        raise ValueError("At least one IoU threshold is required.")
    normalized_predictions = {
        image_id: tuple(
            detection.model_copy(update={"label": _normalize_label(detection.label)})
            for detection in detections
        )
        for image_id, detections in predictions.items()
    }
    ground_truth_count = dataset.total_boxes
    prediction_count = sum(
        1
        for detections in normalized_predictions.values()
        for detection in detections
        if detection.confidence >= operating_confidence
    )
    true_positives, false_positives = _operating_counts(
        dataset,
        normalized_predictions,
        confidence=operating_confidence,
        iou_threshold=0.5,
    )
    precision = _ratio(true_positives, true_positives + false_positives)
    recall = _ratio(true_positives, ground_truth_count)
    f1 = _ratio(2.0 * precision * recall, precision + recall)

    per_class: list[PerClassMetrics] = []
    ap50_values: list[float] = []
    map_values: list[float] = []
    for label in dataset.class_names:
        normalized_label = _normalize_label(label)
        class_ground_truth_count = sum(
            1
            for sample in dataset.samples
            for truth in sample.ground_truth
            if _normalize_label(truth.label) == normalized_label
        )
        if class_ground_truth_count == 0:
            continue
        class_prediction_count = sum(
            1
            for detections in normalized_predictions.values()
            for detection in detections
            if detection.label == normalized_label
            and detection.confidence >= operating_confidence
        )
        class_tp, class_fp = _operating_counts(
            dataset,
            normalized_predictions,
            confidence=operating_confidence,
            iou_threshold=0.5,
            label=normalized_label,
        )
        class_precision = _ratio(class_tp, class_tp + class_fp)
        class_recall = _ratio(class_tp, class_ground_truth_count)
        threshold_aps = tuple(
            _average_precision(
                dataset,
                normalized_predictions,
                label=normalized_label,
                iou_threshold=threshold,
            )
            for threshold in iou_thresholds
        )
        ap50 = threshold_aps[0]
        map50_95 = sum(threshold_aps) / len(threshold_aps)
        ap50_values.append(ap50)
        map_values.append(map50_95)
        per_class.append(
            PerClassMetrics(
                label=label,
                ground_truth_count=class_ground_truth_count,
                prediction_count=class_prediction_count,
                precision=class_precision,
                recall=class_recall,
                ap50=ap50,
                map50_95=map50_95,
            )
        )

    return MetricSummary(
        ground_truth_count=ground_truth_count,
        prediction_count=prediction_count,
        precision=precision,
        recall=recall,
        f1=f1,
        ap50=sum(ap50_values) / len(ap50_values) if ap50_values else 0.0,
        map50_95=sum(map_values) / len(map_values) if map_values else 0.0,
        per_class=tuple(per_class),
    )


def _operating_counts(
    dataset: EvaluationDataset,
    predictions: Mapping[int, tuple[BenchmarkDetection, ...]],
    *,
    confidence: float,
    iou_threshold: float,
    label: str | None = None,
) -> tuple[int, int]:
    true_positives = 0
    false_positives = 0
    for sample in dataset.samples:
        matched_truth: set[int] = set()
        detections = sorted(
            (
                detection
                for detection in predictions.get(sample.image_id, ())
                if detection.confidence >= confidence
                and (label is None or detection.label == label)
            ),
            key=lambda detection: detection.confidence,
            reverse=True,
        )
        for detection in detections:
            best_index = -1
            best_iou = 0.0
            for index, truth in enumerate(sample.ground_truth):
                if index in matched_truth:
                    continue
                truth_label = _normalize_label(truth.label)
                if detection.label != truth_label or (
                    label is not None and truth_label != label
                ):
                    continue
                overlap = detection.box.iou(truth.box)
                if overlap > best_iou:
                    best_iou = overlap
                    best_index = index
            if best_index >= 0 and best_iou >= iou_threshold:
                matched_truth.add(best_index)
                true_positives += 1
            else:
                false_positives += 1
    return true_positives, false_positives


def _average_precision(
    dataset: EvaluationDataset,
    predictions: Mapping[int, tuple[BenchmarkDetection, ...]],
    *,
    label: str,
    iou_threshold: float,
) -> float:
    ground_truth: dict[int, tuple[BenchmarkBox, ...]] = {}
    for sample in dataset.samples:
        boxes = tuple(
            truth.box
            for truth in sample.ground_truth
            if _normalize_label(truth.label) == label
        )
        ground_truth[sample.image_id] = boxes
    total_ground_truth = sum(len(boxes) for boxes in ground_truth.values())
    if total_ground_truth == 0:
        return 0.0

    ranked_predictions = sorted(
        (
            (detection.confidence, image_id, detection.box)
            for image_id, detections in predictions.items()
            for detection in detections
            if detection.label == label
        ),
        key=lambda item: item[0],
        reverse=True,
    )
    matched: dict[int, set[int]] = defaultdict(set)
    cumulative_tp: list[int] = []
    cumulative_fp: list[int] = []
    tp = 0
    fp = 0
    for _, image_id, predicted_box in ranked_predictions:
        best_index = -1
        best_iou = 0.0
        for index, truth_box in enumerate(ground_truth.get(image_id, ())):
            if index in matched[image_id]:
                continue
            overlap = predicted_box.iou(truth_box)
            if overlap > best_iou:
                best_iou = overlap
                best_index = index
        if best_index >= 0 and best_iou >= iou_threshold:
            matched[image_id].add(best_index)
            tp += 1
        else:
            fp += 1
        cumulative_tp.append(tp)
        cumulative_fp.append(fp)

    if not cumulative_tp:
        return 0.0
    recalls = [value / total_ground_truth for value in cumulative_tp]
    precisions = [
        _ratio(cumulative_tp[index], cumulative_tp[index] + cumulative_fp[index])
        for index in range(len(cumulative_tp))
    ]
    interpolated = 0.0
    for recall_step in range(101):
        required_recall = recall_step / 100.0
        interpolated += max(
            (
                precision
                for recall, precision in zip(recalls, precisions, strict=True)
                if recall >= required_recall
            ),
            default=0.0,
        )
    return interpolated / 101.0


def _normalize_label(value: str) -> str:
    return " ".join(value.strip().split()).casefold()


def _ratio(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else 0.0
