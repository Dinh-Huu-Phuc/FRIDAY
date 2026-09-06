from __future__ import annotations

import math
from typing import Any

from friday.app.perception.segmentation.schemas import (
    MaskContour,
    MaskPoint,
    MaskRle,
    SegmentationMask,
)


def encode_binary_mask(mask: Any) -> MaskRle:
    import numpy as np

    values = np.asarray(mask, dtype=np.uint8)
    if values.ndim != 2 or values.shape[0] <= 0 or values.shape[1] <= 0:
        raise ValueError("A segmentation mask must be a non-empty two-dimensional array.")
    values = (values > 0).astype(np.uint8, copy=False)
    height, width = (int(value) for value in values.shape)
    flattened = values.reshape(-1)
    counts: list[int] = []
    current = 0
    run_length = 0
    for value in flattened:
        bit = int(value)
        if bit == current:
            run_length += 1
            continue
        counts.append(run_length)
        run_length = 1
        current = bit
    counts.append(run_length)
    return MaskRle(width=width, height=height, counts=tuple(counts))


def decode_binary_mask(rle: MaskRle) -> Any:
    import numpy as np

    expected = rle.width * rle.height
    if sum(rle.counts) != expected or any(count < 0 for count in rle.counts):
        raise ValueError("The segmentation RLE does not match its declared dimensions.")
    output = np.empty(expected, dtype=np.uint8)
    offset = 0
    bit = 0
    for count in rle.counts:
        output[offset : offset + count] = bit
        offset += count
        bit = 1 - bit
    return output.reshape((rle.height, rle.width))


def build_segmentation_mask(
    mask: Any,
    *,
    maximum_contours: int = 8,
    maximum_points: int = 320,
) -> SegmentationMask:
    import cv2
    import numpy as np

    binary = (np.asarray(mask) > 0).astype(np.uint8)
    if binary.ndim != 2 or binary.shape[0] <= 0 or binary.shape[1] <= 0:
        raise ValueError("SAM 2 returned an invalid mask.")
    height, width = (int(value) for value in binary.shape)
    area = int(binary.sum())
    contours, _ = cv2.findContours(
        binary,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE,
    )
    contours = sorted(contours, key=cv2.contourArea, reverse=True)[:maximum_contours]
    remaining_points = max(3, maximum_points)
    normalized: list[MaskContour] = []
    for contour in contours:
        if remaining_points < 3 or len(contour) < 3:
            break
        perimeter = cv2.arcLength(contour, True)
        simplified = cv2.approxPolyDP(contour, max(1.0, perimeter * 0.0025), True)
        raw_points = simplified.reshape(-1, 2)
        if len(raw_points) > remaining_points:
            stride = max(1, math.ceil(len(raw_points) / remaining_points))
            raw_points = raw_points[::stride]
        if len(raw_points) < 3:
            continue
        points = tuple(
            MaskPoint(
                x=min(1.0, max(0.0, float(x) / max(1, width - 1))),
                y=min(1.0, max(0.0, float(y) / max(1, height - 1))),
            )
            for x, y in raw_points
        )
        normalized.append(MaskContour(points=points))
        remaining_points -= len(points)
    return SegmentationMask(
        width=width,
        height=height,
        area_pixels=area,
        coverage=area / (width * height),
        rle=encode_binary_mask(binary),
        contours=tuple(normalized),
    )
