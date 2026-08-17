from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class MemoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    subject: str
    memory_key: str
    memory_value: str
    memory_type: str
    importance: float
    confidence: float
    source_message_id: UUID | None
    expires_at: datetime | None
    created_at: datetime
    updated_at: datetime
    is_active: bool


class MemoryDeleteResponse(BaseModel):
    ok: bool = True
    memory_id: UUID
