from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Unicode
from sqlalchemy.orm import Mapped, mapped_column, relationship

from friday.src.db.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(Unicode(80), unique=True, nullable=False, index=True)
    email: Mapped[str] = mapped_column(Unicode(255), unique=True, nullable=False, index=True)
    full_name: Mapped[str | None] = mapped_column(Unicode(255), nullable=True)
    password_hash: Mapped[str] = mapped_column(Unicode(255), nullable=False)
    role_id: Mapped[int | None] = mapped_column(ForeignKey("roles.id"), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    free_question_limit_daily: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    api_key_question_limit_daily: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    role = relationship("Role", back_populates="users")
    refresh_tokens = relationship("RefreshToken", back_populates="user")
    api_keys = relationship("InternalApiKey", back_populates="owner")
