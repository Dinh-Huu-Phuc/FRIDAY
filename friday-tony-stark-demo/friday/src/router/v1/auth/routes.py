from __future__ import annotations

from fastapi import APIRouter, Body, Depends, Request, Response
from sqlalchemy.orm import Session

from friday.src.dependencies.auth import require_active_user
from friday.src.dependencies.database import get_db
from friday.src.models.user import User
from friday.src.config.settings import get_settings
from friday.src.schemas.auth.requests import LoginRequest, LogoutRequest, RefreshRequest, RegisterRequest
from friday.src.schemas.auth.responses import LogoutResponse, TokenResponse
from friday.src.schemas.users.responses import UserResponse
from friday.src.services.auth.service import login_user, logout_user, refresh_access_token, register_user


router = APIRouter()


def _set_refresh_cookie(response: Response, token_response: TokenResponse) -> TokenResponse:
    settings = get_settings()
    if token_response.refresh_token:
        response.set_cookie(
            key=settings.refresh_token_cookie_name,
            value=token_response.refresh_token,
            httponly=True,
            secure=settings.refresh_token_cookie_secure,
            samesite=settings.refresh_token_cookie_samesite,
            path=settings.refresh_token_cookie_path,
            max_age=settings.refresh_token_expire_days * 24 * 60 * 60,
        )
    return token_response.model_copy(update={"refresh_token": None})


def _clear_refresh_cookie(response: Response) -> None:
    settings = get_settings()
    response.delete_cookie(
        key=settings.refresh_token_cookie_name,
        path=settings.refresh_token_cookie_path,
    )


def _refresh_token_from_request(request: Request, payload: RefreshRequest | LogoutRequest) -> str | None:
    settings = get_settings()
    return payload.refresh_token or request.cookies.get(settings.refresh_token_cookie_name)


@router.post("/register", response_model=TokenResponse, response_model_exclude_none=True)
def register(
    payload: RegisterRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> TokenResponse:
    return _set_refresh_cookie(response, register_user(db, payload, request))


@router.post("/login", response_model=TokenResponse, response_model_exclude_none=True)
def login(payload: LoginRequest, request: Request, response: Response, db: Session = Depends(get_db)) -> TokenResponse:
    return _set_refresh_cookie(response, login_user(db, payload, request))


@router.post("/logout", response_model=LogoutResponse)
def logout(
    request: Request,
    response: Response,
    payload: LogoutRequest = Body(default_factory=LogoutRequest),
    db: Session = Depends(get_db),
) -> LogoutResponse:
    result = logout_user(db, _refresh_token_from_request(request, payload))
    _clear_refresh_cookie(response)
    return result


@router.get("/me", response_model=UserResponse)
def me(current_user: User = Depends(require_active_user)) -> User:
    return current_user


@router.post("/refresh", response_model=TokenResponse, response_model_exclude_none=True)
def refresh(
    request: Request,
    response: Response,
    payload: RefreshRequest = Body(default_factory=RefreshRequest),
    db: Session = Depends(get_db),
) -> TokenResponse:
    return _set_refresh_cookie(response, refresh_access_token(db, _refresh_token_from_request(request, payload), request))
