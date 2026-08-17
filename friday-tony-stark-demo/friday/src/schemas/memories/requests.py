from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class MemoryRequestBase(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    @field_validator("expires_at", check_fields=False)
    @classmethod
    def validate_expires_at_timezone(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.tzinfo is None:
            raise ValueError("expires_at must include a timezone.")
        return value


class MemoryCreateRequest(MemoryRequestBase):
    subject: str = Field(min_length=1, max_length=30)
    memory_key: str = Field(min_length=1, max_length=150)
    memory_value: str = Field(min_length=1)
    memory_type: str = Field(min_length=1, max_length=30)
    importance: float = Field(default=0.5, ge=0.0, le=1.0)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    source_message_id: UUID | None = None
    expires_at: datetime | None = None


class MemoryUpdateRequest(MemoryRequestBase):
    memory_value: str | None = Field(default=None, min_length=1)
    memory_type: str | None = Field(default=None, min_length=1, max_length=30)
    importance: float | None = Field(default=None, ge=0.0, le=1.0)
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    source_message_id: UUID | None = None
    expires_at: datetime | None = None

    @model_validator(mode="after")
    def require_at_least_one_change(self) -> "MemoryUpdateRequest":
        if not self.model_fields_set:
            raise ValueError("At least one field must be supplied.")
        return self
