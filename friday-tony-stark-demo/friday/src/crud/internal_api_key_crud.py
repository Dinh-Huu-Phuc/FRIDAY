from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from friday.src.models.internal_api_key import InternalApiKey


def create_api_key(
    db: Session,
    *,
    owner_user_id: int | None,
    name: str,
    key_prefix: str,
    key_hash: str,
    scopes_json: str,
    environment: str,
    expires_at: datetime | None,
    rate_limit_per_minute: int | None,
    token_limit_daily: int | None,
    notes: str | None,
) -> InternalApiKey:
    api_key = InternalApiKey(
        owner_user_id=owner_user_id,
        name=name,
        key_prefix=key_prefix,
        key_hash=key_hash,
        scopes_json=scopes_json,
        environment=environment,
        expires_at=expires_at,
        rate_limit_per_minute=rate_limit_per_minute,
        token_limit_daily=token_limit_daily,
        notes=notes,
    )
    db.add(api_key)
    db.commit()
    db.refresh(api_key)
    return api_key


def list_api_keys(db: Session, *, owner_user_id: int | None = None, limit: int = 50, offset: int = 0) -> list[InternalApiKey]:
    statement = select(InternalApiKey).order_by(InternalApiKey.id.desc()).limit(limit).offset(offset)
    if owner_user_id is not None:
        statement = statement.where(InternalApiKey.owner_user_id == owner_user_id)
    return list(db.execute(statement).scalars().all())


def count_api_keys_created_since(db: Session, *, owner_user_id: int, since: datetime) -> int:
    statement = select(func.count()).select_from(InternalApiKey).where(
        InternalApiKey.owner_user_id == owner_user_id,
        InternalApiKey.created_at >= since,
    )
    return int(db.execute(statement).scalar_one())


def get_api_key(db: Session, key_id: int) -> InternalApiKey | None:
    return db.get(InternalApiKey, key_id)


def get_api_key_by_prefix(db: Session, key_prefix: str) -> InternalApiKey | None:
    return db.execute(select(InternalApiKey).where(InternalApiKey.key_prefix == key_prefix)).scalar_one_or_none()


def revoke_api_key(db: Session, api_key: InternalApiKey) -> InternalApiKey:
    api_key.status = "revoked"
    api_key.revoked_at = datetime.now(timezone.utc)
    db.add(api_key)
    db.commit()
    db.refresh(api_key)
    return api_key


def mark_api_key_used(db: Session, api_key: InternalApiKey, ip_address: str | None) -> InternalApiKey:
    api_key.last_used_at = datetime.now(timezone.utc)
    api_key.last_used_ip = ip_address
    api_key.usage_count += 1
    db.add(api_key)
    db.commit()
    db.refresh(api_key)
    return api_key
