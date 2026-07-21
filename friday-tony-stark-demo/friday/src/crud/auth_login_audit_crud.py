from __future__ import annotations

from sqlalchemy.orm import Session

from friday.src.models.auth_login_audit import AuthLoginAudit


def create_login_audit(
    db: Session,
    *,
    user_id: int | None,
    username_or_email: str,
    ip_address: str | None,
    user_agent: str | None,
    success: bool,
    failure_reason: str | None,
) -> AuthLoginAudit:
    audit = AuthLoginAudit(
        user_id=user_id,
        username_or_email=username_or_email,
        ip_address=ip_address,
        user_agent=user_agent,
        success=success,
        failure_reason=failure_reason,
    )
    db.add(audit)
    db.commit()
    db.refresh(audit)
    return audit
