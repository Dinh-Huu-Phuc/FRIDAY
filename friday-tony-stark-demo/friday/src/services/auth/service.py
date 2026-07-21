from __future__ import annotations

from datetime import timedelta

from fastapi import HTTPException, Request, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from friday.src.common.security import (
    create_access_token,
    generate_refresh_token,
    hash_password,
    hash_secret,
    utc_now,
    verify_password,
)
from friday.src.config.settings import get_settings
from friday.src.crud.auth_login_audit_crud import create_login_audit
from friday.src.crud.refresh_token_crud import (
    create_refresh_token,
    get_refresh_token_by_hash,
    revoke_refresh_token,
    revoke_refresh_tokens_for_user,
)
from friday.src.crud.role_crud import get_role_by_name
from friday.src.crud.user_crud import (
    create_user,
    get_user,
    get_user_by_email,
    get_user_by_username,
    get_user_by_username_or_email,
    update_last_login,
)
from friday.src.models.user import User
from friday.src.schemas.auth.requests import LoginRequest, LogoutRequest, RefreshRequest, RegisterRequest
from friday.src.schemas.auth.responses import LogoutResponse, TokenResponse
from friday.src.schemas.users.responses import UserResponse


def _client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


def _issue_tokens(db: Session, user: User, request: Request) -> TokenResponse:
    settings = get_settings()
    access_token = create_access_token(str(user.id), extra_claims={"username": user.username})
    refresh_token = generate_refresh_token()
    create_refresh_token(
        db,
        user_id=user.id,
        token_hash=hash_secret(refresh_token, settings.jwt_secret_key),
        expires_at=utc_now() + timedelta(days=settings.refresh_token_expire_days),
        created_ip=_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.access_token_expire_minutes * 60,
        user=UserResponse.model_validate(user),
    )


def register_user(db: Session, payload: RegisterRequest, request: Request) -> TokenResponse:
    if get_user_by_username(db, payload.username) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already exists.")
    if get_user_by_email(db, payload.email) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already exists.")
    role = get_role_by_name(db, "user")
    try:
        user = create_user(
            db,
            username=payload.username,
            email=payload.email,
            password_hash=hash_password(payload.password),
            full_name=payload.full_name,
            role_id=role.id if role else None,
        )
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User already exists.") from exc
    return _issue_tokens(db, user, request)


def login_user(db: Session, payload: LoginRequest, request: Request) -> TokenResponse:
    user = get_user_by_username_or_email(db, payload.username_or_email)
    if user is None or not verify_password(payload.password, user.password_hash):
        create_login_audit(
            db,
            user_id=user.id if user else None,
            username_or_email=payload.username_or_email,
            ip_address=_client_ip(request),
            user_agent=request.headers.get("user-agent"),
            success=False,
            failure_reason="invalid_credentials",
        )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username/email or password.")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is disabled.")
    update_last_login(db, user, utc_now())
    create_login_audit(
        db,
        user_id=user.id,
        username_or_email=payload.username_or_email,
        ip_address=_client_ip(request),
        user_agent=request.headers.get("user-agent"),
        success=True,
        failure_reason=None,
    )
    return _issue_tokens(db, user, request)


def refresh_access_token(db: Session, refresh_token: str | None, request: Request) -> TokenResponse:
    settings = get_settings()
    if not refresh_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing refresh token.")
    token_row = get_refresh_token_by_hash(db, hash_secret(refresh_token, settings.jwt_secret_key))
    if token_row is None or token_row.expires_at < utc_now():
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token.")
    if token_row.revoked_at is not None:
        revoke_refresh_tokens_for_user(db, token_row.user_id)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token was already used.")
    user = get_user(db, token_row.user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User is unavailable.")
    revoke_refresh_token(db, token_row)
    return _issue_tokens(db, user, request)


def logout_user(db: Session, refresh_token: str | None) -> LogoutResponse:
    settings = get_settings()
    if not refresh_token:
        return LogoutResponse()
    token_row = get_refresh_token_by_hash(db, hash_secret(refresh_token, settings.jwt_secret_key))
    if token_row is not None and token_row.revoked_at is None:
        revoke_refresh_token(db, token_row)
    return LogoutResponse()
