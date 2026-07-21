from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, Unicode, UnicodeText
from sqlalchemy.orm import Mapped, mapped_column, relationship

from friday.src.db.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class InternalApiKeyUsageLog(Base):
    __tablename__ = "internal_api_key_usage_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    api_key_id: Mapped[int] = mapped_column(ForeignKey("internal_api_keys.id"), nullable=False, index=True)
    endpoint: Mapped[str] = mapped_column(Unicode(255), nullable=False)
    method: Mapped[str] = mapped_column(Unicode(16), nullable=False)
    ip_address: Mapped[str | None] = mapped_column(Unicode(64), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(UnicodeText, nullable=True)
    status_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tokens_used: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    api_key = relationship("InternalApiKey", back_populates="usage_logs")
