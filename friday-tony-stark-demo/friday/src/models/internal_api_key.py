from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, Unicode, UnicodeText
from sqlalchemy.orm import Mapped, mapped_column, relationship

from friday.src.db.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class InternalApiKey(Base):
    __tablename__ = "internal_api_keys"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    owner_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    name: Mapped[str] = mapped_column(Unicode(120), nullable=False)
    key_prefix: Mapped[str] = mapped_column(Unicode(48), nullable=False, unique=True, index=True)
    key_hash: Mapped[str] = mapped_column(Unicode(255), nullable=False, unique=True, index=True)
    scopes_json: Mapped[str] = mapped_column(UnicodeText, default="[]", nullable=False)
    status: Mapped[str] = mapped_column(Unicode(32), default="active", nullable=False, index=True)
    environment: Mapped[str] = mapped_column(Unicode(32), default="local", nullable=False, index=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_used_ip: Mapped[str | None] = mapped_column(Unicode(64), nullable=True)
    usage_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    rate_limit_per_minute: Mapped[int | None] = mapped_column(Integer, nullable=True)
    token_limit_daily: Mapped[int | None] = mapped_column(Integer, nullable=True)
    token_used_today: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    daily_reset_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(UnicodeText, nullable=True)

    owner = relationship("User", back_populates="api_keys")
    usage_logs = relationship("InternalApiKeyUsageLog", back_populates="api_key")
