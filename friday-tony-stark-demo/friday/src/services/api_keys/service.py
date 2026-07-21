from __future__ import annotations

import json
from datetime import datetime, time, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from friday.src.common.security import generate_internal_api_key, hash_secret, verify_secret
from friday.src.crud.internal_api_key_crud import (
    count_api_keys_created_since,
    create_api_key,
    get_api_key,
    get_api_key_by_prefix,
    list_api_keys,
    revoke_api_key,
)
from friday.src.models.internal_api_key import InternalApiKey
from friday.src.models.user import User
from friday.src.schemas.api_keys.requests import ApiKeyCreateRequest
from friday.src.schemas.api_keys.responses import ApiKeyCreateResponse, ApiKeyMetadataResponse


FREE_KEY_DAILY_REQUEST_LIMIT = 10
DAILY_KEY_CREATE_LIMIT = 1


def _is_admin(user: User) -> bool:
    return user.role is not None and user.role.name == "admin"


def _utc_day_start(value: datetime | None = None) -> datetime:
    current = value or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    return datetime.combine(current.date(), time.min, tzinfo=timezone.utc)


def _as_utc(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


def _reset_daily_usage_if_needed(db: Session, api_key: InternalApiKey) -> InternalApiKey:
    today_start = _utc_day_start()
    if api_key.daily_reset_at is None or _as_utc(api_key.daily_reset_at) < today_start:
        api_key.token_used_today = 0
        api_key.daily_reset_at = today_start
        db.add(api_key)
        db.commit()
        db.refresh(api_key)
    return api_key


def _metadata(api_key: InternalApiKey) -> ApiKeyMetadataResponse:
    return ApiKeyMetadataResponse(
        id=api_key.id,
        owner_user_id=api_key.owner_user_id,
        name=api_key.name,
        key_prefix=api_key.key_prefix,
        scopes=json.loads(api_key.scopes_json or "[]"),
        status=api_key.status,
        environment=api_key.environment,
        expires_at=api_key.expires_at,
        revoked_at=api_key.revoked_at,
        created_at=api_key.created_at,
        updated_at=api_key.updated_at,
        last_used_at=api_key.last_used_at,
        last_used_ip=api_key.last_used_ip,
        usage_count=api_key.usage_count,
        rate_limit_per_minute=api_key.rate_limit_per_minute,
        token_limit_daily=api_key.token_limit_daily,
        token_used_today=api_key.token_used_today,
        daily_reset_at=api_key.daily_reset_at,
        notes=api_key.notes,
    )


def create_internal_api_key(db: Session, payload: ApiKeyCreateRequest, current_user: User) -> ApiKeyCreateResponse:
    created_today = count_api_keys_created_since(
        db,
        owner_user_id=current_user.id,
        since=_utc_day_start(),
    )
    if created_today >= DAILY_KEY_CREATE_LIMIT:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Daily API key creation limit reached. Each account can create 1 key per day.",
        )

    full_key, key_prefix = generate_internal_api_key(payload.environment)
    row = create_api_key(
        db,
        owner_user_id=current_user.id,
        name=payload.name,
        key_prefix=key_prefix,
        key_hash=hash_secret(full_key),
        scopes_json=json.dumps(payload.scopes),
        environment=payload.environment,
        expires_at=payload.expires_at,
        rate_limit_per_minute=payload.rate_limit_per_minute,
        token_limit_daily=current_user.api_key_question_limit_daily or FREE_KEY_DAILY_REQUEST_LIMIT,
        notes=payload.notes,
    )
    return ApiKeyCreateResponse(api_key=full_key, metadata=_metadata(row))


def list_internal_api_keys(db: Session, current_user: User, limit: int = 50, offset: int = 0) -> list[ApiKeyMetadataResponse]:
    owner_id = None if _is_admin(current_user) else current_user.id
    return [_metadata(row) for row in list_api_keys(db, owner_user_id=owner_id, limit=limit, offset=offset)]


def get_internal_api_key(db: Session, current_user: User, key_id: int) -> ApiKeyMetadataResponse:
    row = get_api_key(db, key_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API key not found.")
    if not _is_admin(current_user) and row.owner_user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot view another user's API key.")
    return _metadata(row)


def revoke_internal_api_key(db: Session, current_user: User, key_id: int) -> ApiKeyMetadataResponse:
    row = get_api_key(db, key_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API key not found.")
    if not _is_admin(current_user) and row.owner_user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot revoke another user's API key.")
    if row.status != "revoked":
        row = revoke_api_key(db, row)
    if row.expires_at is not None and row.expires_at < datetime.now(timezone.utc):
        row.status = "expired"
        db.add(row)
        db.commit()
        db.refresh(row)
    return _metadata(row)


def verify_internal_api_key(db: Session, api_key: str, current_user: User) -> ApiKeyMetadataResponse:
    key_prefix = api_key[:24]
    row = get_api_key_by_prefix(db, key_prefix)
    if row is None or not verify_secret(api_key, row.key_hash):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API key not found.")
    if not _is_admin(current_user) and row.owner_user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot use another user's API key.")
    if row.status != "active":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="API key is not active.")
    if row.expires_at is not None and row.expires_at < datetime.now(timezone.utc):
        row.status = "expired"
        db.add(row)
        db.commit()
        db.refresh(row)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="API key has expired.")
    return _metadata(_reset_daily_usage_if_needed(db, row))


def consume_internal_api_key_quota(db: Session, current_user: User, key_id: int) -> tuple[ApiKeyMetadataResponse, int | None]:
    row = get_api_key(db, key_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API key not found.")
    if not _is_admin(current_user) and row.owner_user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot use another user's API key.")
    if row.status != "active":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="API key is not active.")
    if row.expires_at is not None and row.expires_at < datetime.now(timezone.utc):
        row.status = "expired"
        db.add(row)
        db.commit()
        db.refresh(row)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="API key has expired.")

    row = _reset_daily_usage_if_needed(db, row)
    daily_limit = row.token_limit_daily or FREE_KEY_DAILY_REQUEST_LIMIT
    if row.token_used_today >= daily_limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Daily API key usage limit reached.",
        )

    row.token_used_today += 1
    row.usage_count += 1
    row.last_used_at = datetime.now(timezone.utc)
    db.add(row)
    db.commit()
    db.refresh(row)
    return _metadata(row), max(daily_limit - row.token_used_today, 0)
