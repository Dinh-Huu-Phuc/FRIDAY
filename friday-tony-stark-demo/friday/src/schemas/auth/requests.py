from __future__ import annotations

from pydantic import BaseModel, Field

from friday.src.schemas.users.requests import UserCreateRequest


class RegisterRequest(UserCreateRequest):
    pass


class LoginRequest(BaseModel):
    username_or_email: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=1, max_length=256)


class RefreshRequest(BaseModel):
    refresh_token: str | None = Field(default=None, min_length=16)


class LogoutRequest(BaseModel):
    refresh_token: str | None = Field(default=None, min_length=16)
