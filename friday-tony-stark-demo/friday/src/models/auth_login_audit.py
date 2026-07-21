from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Unicode, UnicodeText
from sqlalchemy.orm import Mapped, mapped_column

from friday.src.db.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class AuthLoginAudit(Base):
    __tablename__ = "auth_login_audits"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    username_or_email: Mapped[str] = mapped_column(Unicode(255), nullable=False)
    ip_address: Mapped[str | None] = mapped_column(Unicode(64), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(UnicodeText, nullable=True)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False)
    failure_reason: Mapped[str | None] = mapped_column(UnicodeText, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
