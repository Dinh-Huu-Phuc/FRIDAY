from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import CheckConstraint, DateTime, Integer, Unicode
from sqlalchemy.orm import Mapped, mapped_column

from friday.src.db.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class CoreAccessCredential(Base):
    __tablename__ = "core_access_credentials"
    __table_args__ = (
        CheckConstraint("id = 1", name="ck_core_access_credentials_singleton"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    password_hash: Mapped[str] = mapped_column(Unicode(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )
