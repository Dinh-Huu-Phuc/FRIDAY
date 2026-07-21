from __future__ import annotations

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from friday.src.common.security import decode_access_token
from friday.src.crud.admin_account_crud import get_admin_account
from friday.src.dependencies.database import get_db
from friday.src.models.admin_account import AdminAccount


admin_bearer_scheme = HTTPBearer(auto_error=False)


def get_current_admin(
    credentials: HTTPAuthorizationCredentials | None = Depends(admin_bearer_scheme),
    db: Session = Depends(get_db),
) -> AdminAccount:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing admin bearer token.")
    try:
        payload = decode_access_token(credentials.credentials)
        if payload.get("scope") != "admin":
            raise ValueError("Not an admin token.")
        admin_id = int(payload["sub"])
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid admin bearer token.") from exc
    admin = get_admin_account(db, admin_id)
    if admin is None or not admin.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Admin account is unavailable.")
    return admin


def require_super_admin(current_admin: AdminAccount = Depends(get_current_admin)) -> AdminAccount:
    if current_admin.role != "super_admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Super admin role required.")
    return current_admin
