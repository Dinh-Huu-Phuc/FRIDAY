from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ApiKeyMetadataResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    owner_user_id: int | None
    name: str
    key_prefix: str
    scopes: list[str]
    status: str
    environment: str
    expires_at: datetime | None
    revoked_at: datetime | None
    created_at: datetime
    updated_at: datetime
    last_used_at: datetime | None
    last_used_ip: str | None
    usage_count: int
    rate_limit_per_minute: int | None
    token_limit_daily: int | None
    token_used_today: int
    daily_reset_at: datetime | None
    notes: str | None


class ApiKeyCreateResponse(BaseModel):
    api_key: str
    metadata: ApiKeyMetadataResponse


class ApiKeyRevokeResponse(BaseModel):
    ok: bool = True
    api_key: ApiKeyMetadataResponse


class ApiKeyVerifyResponse(BaseModel):
    ok: bool = True
    api_key: ApiKeyMetadataResponse


class ApiKeyConsumeResponse(BaseModel):
    ok: bool = True
    api_key: ApiKeyMetadataResponse
    remaining: int | None
