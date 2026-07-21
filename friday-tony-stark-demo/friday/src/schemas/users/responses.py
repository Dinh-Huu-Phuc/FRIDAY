from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class RoleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None = None


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: str
    full_name: str | None = None
    role_id: int | None = None
    is_active: bool
    is_verified: bool
    free_question_limit_daily: int = 10
    api_key_question_limit_daily: int = 10
    last_login_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
