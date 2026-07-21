from __future__ import annotations

import json
from datetime import datetime, time, timezone

from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session

from friday.src.common.security import hash_secret
from friday.src.crud.internal_api_key_crud import get_api_key_by_prefix, mark_api_key_used
from friday.src.crud.internal_api_key_usage_log_crud import create_usage_log
from friday.src.dependencies.database import get_db
from friday.src.models.internal_api_key import InternalApiKey


FREE_KEY_DAILY_REQUEST_LIMIT = 10


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


def verify_internal_api_key(
    request: Request,
    x_friday_api_key: str | None = Header(default=None, alias="X-Friday-API-Key"),
    db: Session = Depends(get_db),
    required_scopes: set[str] | None = None,
) -> InternalApiKey:
    if not x_friday_api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing X-Friday-API-Key header.")

    key_prefix = x_friday_api_key[:24]
    api_key = get_api_key_by_prefix(db, key_prefix)
    if api_key is None or api_key.key_hash != hash_secret(x_friday_api_key):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key.")

    now = datetime.now(timezone.utc)
    if api_key.status != "active":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="API key is not active.")
    if api_key.expires_at is not None and api_key.expires_at < now:
        api_key.status = "expired"
        db.add(api_key)
        db.commit()
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="API key has expired.")

    scopes = set(json.loads(api_key.scopes_json or "[]"))
    if required_scopes and not required_scopes.issubset(scopes):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="API key scope is insufficient.")

    api_key = _reset_daily_usage_if_needed(db, api_key)
    daily_limit = api_key.token_limit_daily or FREE_KEY_DAILY_REQUEST_LIMIT
    if api_key.token_used_today >= daily_limit:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Daily API key usage limit reached.")
    api_key.token_used_today += 1
    db.add(api_key)
    db.commit()
    db.refresh(api_key)

    client_host = request.client.host if request.client else None
    mark_api_key_used(db, api_key, client_host)
    create_usage_log(
        db,
        api_key_id=api_key.id,
        endpoint=request.url.path,
        method=request.method,
        ip_address=client_host,
        user_agent=request.headers.get("user-agent"),
    )
    return api_key
