from __future__ import annotations

from pydantic import BaseModel

from friday.src.schemas.users.responses import UserResponse


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str | None = None
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse


class LogoutResponse(BaseModel):
    ok: bool = True
    message: str = "logged out"
