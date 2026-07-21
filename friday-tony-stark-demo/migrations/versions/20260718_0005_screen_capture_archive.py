"""add screen capture archive metadata

Revision ID: 20260718_0005
Revises: 20260716_0004
Create Date: 2026-07-18
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260718_0005"
down_revision = "20260716_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "screen_captures",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("user_question", sa.Text(), nullable=True),
        sa.Column("active_window_title", sa.Text(), nullable=True),
        sa.Column("monitor_count", sa.Integer(), nullable=False),
        sa.Column("status", sa.Unicode(length=20), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "monitor_count > 0",
            name="ck_screen_captures_monitor_count",
        ),
        sa.CheckConstraint(
            "status in ('pending', 'uploaded', 'failed')",
            name="ck_screen_captures_status",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "screen_capture_assets",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("capture_id", sa.Uuid(), nullable=False),
        sa.Column("monitor_index", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("screen_width", sa.Integer(), nullable=False),
        sa.Column("screen_height", sa.Integer(), nullable=False),
        sa.Column("storage_bucket", sa.Unicode(length=100), nullable=False),
        sa.Column("storage_path", sa.Text(), nullable=False),
        sa.Column("original_filename", sa.Text(), nullable=False),
        sa.Column("mime_type", sa.Unicode(length=64), nullable=False),
        sa.Column("byte_size", sa.BigInteger(), nullable=False),
        sa.Column("sha256", sa.Unicode(length=64), nullable=False),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "byte_size >= 0",
            name="ck_screen_capture_assets_byte_size",
        ),
        sa.CheckConstraint(
            "monitor_index > 0",
            name="ck_screen_capture_assets_monitor_index",
        ),
        sa.CheckConstraint(
            "screen_height > 0",
            name="ck_screen_capture_assets_height",
        ),
        sa.CheckConstraint(
            "screen_width > 0",
            name="ck_screen_capture_assets_width",
        ),
        sa.ForeignKeyConstraint(
            ["capture_id"],
            ["screen_captures.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "capture_id",
            "monitor_index",
            name="uq_screen_capture_assets_capture_monitor",
        ),
        sa.UniqueConstraint(
            "storage_bucket",
            "storage_path",
            name="uq_screen_capture_assets_storage_object",
        ),
    )

    op.execute("ALTER TABLE screen_captures ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE screen_capture_assets ENABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    op.drop_table("screen_capture_assets")
    op.drop_table("screen_captures")
