from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class AdminLoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=1)


class AdminCreateRequest(BaseModel):
    username: str = Field(min_length=3, max_length=80)
    password: str = Field(min_length=8)
    display_name: str | None = None


class AdminAccountResponse(BaseModel):
    id: int
    username: str
    display_name: str | None = None
    role: str
    is_active: bool
    last_login_at: datetime | None = None
    created_at: datetime


class AdminTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    admin: AdminAccountResponse


class AdminUserQuotaUpdateRequest(BaseModel):
    free_question_limit_daily: int | None = Field(default=None, ge=0, le=100000)
    api_key_question_limit_daily: int | None = Field(default=None, ge=0, le=100000)
    is_active: bool | None = None


class AdminApiKeyQuotaUpdateRequest(BaseModel):
    token_limit_daily: int = Field(ge=0, le=100000)
