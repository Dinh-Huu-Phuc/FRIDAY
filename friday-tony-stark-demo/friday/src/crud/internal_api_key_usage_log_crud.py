from __future__ import annotations

from sqlalchemy.orm import Session

from friday.src.models.internal_api_key_usage_log import InternalApiKeyUsageLog


def create_usage_log(
    db: Session,
    *,
    api_key_id: int,
    endpoint: str,
    method: str,
    ip_address: str | None,
    user_agent: str | None,
    status_code: int | None = None,
    tokens_used: int = 0,
) -> InternalApiKeyUsageLog:
    log = InternalApiKeyUsageLog(
        api_key_id=api_key_id,
        endpoint=endpoint,
        method=method,
        ip_address=ip_address,
        user_agent=user_agent,
        status_code=status_code,
        tokens_used=tokens_used,
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log
