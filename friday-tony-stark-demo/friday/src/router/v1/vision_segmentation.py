from __future__ import annotations

from fastapi import APIRouter

from friday.app.perception.detection import BoundingBox
from friday.app.perception.segmentation import (
    SegmentationCapabilities,
    SegmentationResult,
    get_segmentation_service,
)
from friday.src.schemas.vision_segmentation import (
    BoxSegmentationRequest,
    CameraSegmentationRequest,
    ClearSegmentationRequest,
)

router = APIRouter()


@router.get("/capabilities", response_model=SegmentationCapabilities)
def segmentation_capabilities() -> SegmentationCapabilities:
    return get_segmentation_service().capabilities()


@router.get("/current", response_model=SegmentationResult)
def current_segmentation() -> SegmentationResult:
    return get_segmentation_service().current()


@router.post("/current", response_model=SegmentationResult)
async def segment_current_frame(
    payload: CameraSegmentationRequest,
) -> SegmentationResult:
    return await get_segmentation_service().segment_current(
        payload.target,
        precise_tracking=payload.precise_tracking,
    )


@router.post("/box", response_model=SegmentationResult)
async def segment_camera_box(payload: BoxSegmentationRequest) -> SegmentationResult:
    return await get_segmentation_service().segment_box(
        BoundingBox(payload.x1, payload.y1, payload.x2, payload.y2),
        target_label=payload.target,
        precise_tracking=payload.precise_tracking,
    )


@router.post("/tracking/stop", response_model=SegmentationResult)
def stop_segmentation_tracking() -> SegmentationResult:
    return get_segmentation_service().stop_tracking()


@router.delete("/current", response_model=SegmentationResult)
def clear_segmentation(
    payload: ClearSegmentationRequest | None = None,
) -> SegmentationResult:
    return get_segmentation_service().clear(
        unload_model=False if payload is None else payload.unload_model
    )
