from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from friday.core.memory_database import (
    InvalidMemoryQueryError,
    MemoryNotFoundError,
    MemoryRepository,
    MemoryService,
)
from friday.src.dependencies.database import get_db
from friday.src.schemas.memories import (
    MemoryCreateRequest,
    MemoryDeleteResponse,
    MemoryResponse,
    MemoryUpdateRequest,
)


router = APIRouter()


def _service(db: Session) -> MemoryService:
    return MemoryService(MemoryRepository(db))


def _bad_request(exc: InvalidMemoryQueryError) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        detail=str(exc),
    )


def _not_found(exc: MemoryNotFoundError) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.get("", response_model=list[MemoryResponse])
def list_memories(
    subject: str | None = Query(default=None, max_length=30),
    memory_type: str | None = Query(default=None, max_length=30),
    include_inactive: bool = False,
    include_expired: bool = False,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> list[MemoryResponse]:
    try:
        return _service(db).list(
            subject=subject,
            memory_type=memory_type,
            include_inactive=include_inactive,
            include_expired=include_expired,
            limit=limit,
            offset=offset,
        )
    except InvalidMemoryQueryError as exc:
        raise _bad_request(exc) from exc


@router.get("/relevant", response_model=list[MemoryResponse])
def relevant_memories(
    subject: str | None = Query(default=None, max_length=30),
    memory_type: str | None = Query(default=None, max_length=30),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> list[MemoryResponse]:
    try:
        return _service(db).relevant(
            subject=subject,
            memory_type=memory_type,
            limit=limit,
        )
    except InvalidMemoryQueryError as exc:
        raise _bad_request(exc) from exc


@router.get("/{memory_id}", response_model=MemoryResponse)
def get_memory(
    memory_id: UUID,
    db: Session = Depends(get_db),
) -> MemoryResponse:
    try:
        return _service(db).get(memory_id)
    except MemoryNotFoundError as exc:
        raise _not_found(exc) from exc


@router.post("", response_model=MemoryResponse)
def upsert_memory(
    payload: MemoryCreateRequest,
    db: Session = Depends(get_db),
) -> MemoryResponse:
    try:
        return _service(db).upsert(payload.model_dump())
    except InvalidMemoryQueryError as exc:
        raise _bad_request(exc) from exc


@router.patch("/{memory_id}", response_model=MemoryResponse)
def update_memory(
    memory_id: UUID,
    payload: MemoryUpdateRequest,
    db: Session = Depends(get_db),
) -> MemoryResponse:
    try:
        return _service(db).update(
            memory_id,
            payload.model_dump(exclude_unset=True),
        )
    except InvalidMemoryQueryError as exc:
        raise _bad_request(exc) from exc
    except MemoryNotFoundError as exc:
        raise _not_found(exc) from exc


@router.post("/{memory_id}/deactivate", response_model=MemoryResponse)
def deactivate_memory(
    memory_id: UUID,
    db: Session = Depends(get_db),
) -> MemoryResponse:
    try:
        return _service(db).deactivate(memory_id)
    except MemoryNotFoundError as exc:
        raise _not_found(exc) from exc


@router.post("/{memory_id}/reactivate", response_model=MemoryResponse)
def reactivate_memory(
    memory_id: UUID,
    db: Session = Depends(get_db),
) -> MemoryResponse:
    try:
        return _service(db).reactivate(memory_id)
    except MemoryNotFoundError as exc:
        raise _not_found(exc) from exc


@router.delete("/{memory_id}", response_model=MemoryDeleteResponse)
def delete_memory(
    memory_id: UUID,
    db: Session = Depends(get_db),
) -> MemoryDeleteResponse:
    try:
        _service(db).delete(memory_id)
    except MemoryNotFoundError as exc:
        raise _not_found(exc) from exc
    return MemoryDeleteResponse(memory_id=memory_id)
