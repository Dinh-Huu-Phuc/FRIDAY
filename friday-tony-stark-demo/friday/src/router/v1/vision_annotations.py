from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from friday.app.perception.annotation import (
    AnnotationBox,
    AnnotationConflictError,
    AnnotationNotFoundError,
    AnnotationProposal,
    AnnotationSource,
    AnnotationStatus,
    AnnotationSummary,
    AnnotationUnavailableError,
    AnnotationValidationError,
    get_annotation_service,
)
from friday.src.schemas.vision_annotations import (
    AnnotationApprovalRequest,
    AnnotationCorrectionRequest,
    AnnotationRejectionRequest,
    CameraAnnotationProposalRequest,
)

router = APIRouter()


def _translate_error(exc: Exception) -> HTTPException:
    if isinstance(exc, AnnotationNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    if isinstance(exc, AnnotationConflictError):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    if isinstance(exc, AnnotationUnavailableError):
        return HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        )
    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        detail=str(exc),
    )


@router.get("", response_model=list[AnnotationProposal])
def list_annotations(
    annotation_status: Annotated[
        AnnotationStatus | None,
        Query(alias="status"),
    ] = None,
) -> list[AnnotationProposal]:
    return get_annotation_service().list(annotation_status)


@router.get("/summary", response_model=AnnotationSummary)
def annotation_summary() -> AnnotationSummary:
    return get_annotation_service().summary()


@router.get("/{proposal_id}", response_model=AnnotationProposal)
def get_annotation(proposal_id: UUID) -> AnnotationProposal:
    try:
        return get_annotation_service().get(proposal_id)
    except AnnotationNotFoundError as exc:
        raise _translate_error(exc) from exc


@router.post(
    "/proposals/camera",
    response_model=AnnotationProposal,
    status_code=status.HTTP_201_CREATED,
)
def propose_camera_annotation(
    payload: CameraAnnotationProposalRequest,
) -> AnnotationProposal:
    try:
        return get_annotation_service().propose_from_camera(payload.labels)
    except (AnnotationUnavailableError, AnnotationValidationError) as exc:
        raise _translate_error(exc) from exc


@router.patch("/{proposal_id}", response_model=AnnotationProposal)
def correct_annotation(
    proposal_id: UUID,
    payload: AnnotationCorrectionRequest,
) -> AnnotationProposal:
    boxes = None
    if payload.boxes is not None:
        boxes = tuple(
            AnnotationBox(
                label=box.label,
                confidence=box.confidence,
                x1=box.x1,
                y1=box.y1,
                x2=box.x2,
                y2=box.y2,
                source=AnnotationSource.HUMAN,
            )
            for box in payload.boxes
        )
    try:
        return get_annotation_service().correct(
            proposal_id,
            boxes=boxes,
            review_note=payload.review_note,
        )
    except (
        AnnotationConflictError,
        AnnotationNotFoundError,
        AnnotationValidationError,
    ) as exc:
        raise _translate_error(exc) from exc


@router.post("/{proposal_id}/approve", response_model=AnnotationProposal)
def approve_annotation(
    proposal_id: UUID,
    payload: AnnotationApprovalRequest | None = None,
) -> AnnotationProposal:
    try:
        return get_annotation_service().approve(
            proposal_id,
            review_note=None if payload is None else payload.review_note,
        )
    except (
        AnnotationConflictError,
        AnnotationNotFoundError,
        AnnotationValidationError,
    ) as exc:
        raise _translate_error(exc) from exc


@router.post("/{proposal_id}/reject", response_model=AnnotationProposal)
def reject_annotation(
    proposal_id: UUID,
    payload: AnnotationRejectionRequest,
) -> AnnotationProposal:
    try:
        return get_annotation_service().reject(proposal_id, payload.reason)
    except (
        AnnotationConflictError,
        AnnotationNotFoundError,
        AnnotationValidationError,
    ) as exc:
        raise _translate_error(exc) from exc
