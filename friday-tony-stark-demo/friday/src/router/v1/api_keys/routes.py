from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from friday.src.dependencies.auth import require_active_user
from friday.src.dependencies.database import get_db
from friday.src.models.user import User
from friday.src.schemas.api_keys.requests import ApiKeyCreateRequest, ApiKeyVerifyRequest
from friday.src.schemas.api_keys.responses import (
    ApiKeyConsumeResponse,
    ApiKeyCreateResponse,
    ApiKeyMetadataResponse,
    ApiKeyRevokeResponse,
    ApiKeyVerifyResponse,
)
from friday.src.services.api_keys.service import (
    consume_internal_api_key_quota,
    create_internal_api_key,
    get_internal_api_key,
    list_internal_api_keys,
    revoke_internal_api_key,
    verify_internal_api_key,
)


router = APIRouter()


@router.post("", response_model=ApiKeyCreateResponse)
def create_key(
    payload: ApiKeyCreateRequest,
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
) -> ApiKeyCreateResponse:
    return create_internal_api_key(db, payload, current_user)


@router.get("", response_model=list[ApiKeyMetadataResponse])
def list_keys(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
) -> list[ApiKeyMetadataResponse]:
    return list_internal_api_keys(db, current_user, limit=limit, offset=offset)


@router.post("/verify", response_model=ApiKeyVerifyResponse)
def verify_key(
    payload: ApiKeyVerifyRequest,
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
) -> ApiKeyVerifyResponse:
    return ApiKeyVerifyResponse(api_key=verify_internal_api_key(db, payload.api_key, current_user))


@router.post("/{key_id}/consume-quota", response_model=ApiKeyConsumeResponse)
def consume_key_quota(
    key_id: int,
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
) -> ApiKeyConsumeResponse:
    api_key, remaining = consume_internal_api_key_quota(db, current_user, key_id)
    return ApiKeyConsumeResponse(api_key=api_key, remaining=remaining)


@router.get("/{key_id}", response_model=ApiKeyMetadataResponse)
def get_key(
    key_id: int,
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
) -> ApiKeyMetadataResponse:
    return get_internal_api_key(db, current_user, key_id)


@router.post("/{key_id}/revoke", response_model=ApiKeyRevokeResponse)
def revoke_key(
    key_id: int,
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
) -> ApiKeyRevokeResponse:
    return ApiKeyRevokeResponse(api_key=revoke_internal_api_key(db, current_user, key_id))


@router.delete("/{key_id}", response_model=ApiKeyRevokeResponse)
def delete_key(
    key_id: int,
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
) -> ApiKeyRevokeResponse:
    return ApiKeyRevokeResponse(api_key=revoke_internal_api_key(db, current_user, key_id))
