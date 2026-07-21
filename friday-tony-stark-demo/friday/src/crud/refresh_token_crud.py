from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from friday.src.models.refresh_token import RefreshToken


def create_refresh_token(
    db: Session,
    *,
    user_id: int,
    token_hash: str,
    expires_at: datetime,
    created_ip: str | None,
    user_agent: str | None,
) -> RefreshToken:
    token = RefreshToken(
        user_id=user_id,
        token_hash=token_hash,
        expires_at=expires_at,
        created_ip=created_ip,
        user_agent=user_agent,
    )
    db.add(token)
    db.commit()
    db.refresh(token)
    return token


def get_refresh_token_by_hash(db: Session, token_hash: str) -> RefreshToken | None:
    return db.execute(select(RefreshToken).where(RefreshToken.token_hash == token_hash)).scalar_one_or_none()


def revoke_refresh_token(db: Session, token: RefreshToken) -> RefreshToken:
    token.revoked_at = datetime.now(timezone.utc)
    db.add(token)
    db.commit()
    db.refresh(token)
    return token


def revoke_refresh_tokens_for_user(db: Session, user_id: int) -> int:
    tokens = db.execute(
        select(RefreshToken).where(
            RefreshToken.user_id == user_id,
            RefreshToken.revoked_at.is_(None),
        )
    ).scalars().all()
    revoked_at = datetime.now(timezone.utc)
    for token in tokens:
        token.revoked_at = revoked_at
        db.add(token)
    db.commit()
    return len(tokens)
