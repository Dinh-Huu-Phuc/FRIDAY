from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Text,
    Unicode,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from friday.src.db.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ScreenCaptureRecord(Base):
    __tablename__ = "screen_captures"
    __table_args__ = (
        CheckConstraint(
            "status in ('pending', 'uploaded', 'failed')",
            name="ck_screen_captures_status",
        ),
        CheckConstraint("monitor_count > 0", name="ck_screen_captures_monitor_count"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    user_question: Mapped[str | None] = mapped_column(Text, nullable=True)
    active_window_title: Mapped[str | None] = mapped_column(Text, nullable=True)
    monitor_count: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(Unicode(20), nullable=False, default="pending")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )


class ScreenCaptureAsset(Base):
    __tablename__ = "screen_capture_assets"
    __table_args__ = (
        UniqueConstraint(
            "capture_id",
            "monitor_index",
            name="uq_screen_capture_assets_capture_monitor",
        ),
        UniqueConstraint(
            "storage_bucket",
            "storage_path",
            name="uq_screen_capture_assets_storage_object",
        ),
        CheckConstraint("monitor_index > 0", name="ck_screen_capture_assets_monitor_index"),
        CheckConstraint("screen_width > 0", name="ck_screen_capture_assets_width"),
        CheckConstraint("screen_height > 0", name="ck_screen_capture_assets_height"),
        CheckConstraint("byte_size >= 0", name="ck_screen_capture_assets_byte_size"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    capture_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("screen_captures.id", ondelete="CASCADE"),
        nullable=False,
    )
    monitor_index: Mapped[int] = mapped_column(Integer, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    screen_width: Mapped[int] = mapped_column(Integer, nullable=False)
    screen_height: Mapped[int] = mapped_column(Integer, nullable=False)
    storage_bucket: Mapped[str] = mapped_column(Unicode(100), nullable=False)
    storage_path: Mapped[str] = mapped_column(Text, nullable=False)
    original_filename: Mapped[str] = mapped_column(Text, nullable=False)
    mime_type: Mapped[str] = mapped_column(Unicode(64), nullable=False)
    byte_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    sha256: Mapped[str] = mapped_column(Unicode(64), nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
