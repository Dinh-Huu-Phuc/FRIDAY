"""add admin accounts and per-user quotas

Revision ID: 20260513_0003
Revises: 20260430_0002
Create Date: 2026-05-13
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260513_0003"
down_revision = "20260430_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("free_question_limit_daily", sa.Integer(), nullable=False, server_default="10"))
    op.add_column("users", sa.Column("api_key_question_limit_daily", sa.Integer(), nullable=False, server_default="10"))

    op.create_table(
        "admin_accounts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("username", sa.Unicode(length=80), nullable=False),
        sa.Column("password_hash", sa.Unicode(length=255), nullable=False),
        sa.Column("display_name", sa.Unicode(length=255), nullable=True),
        sa.Column("role", sa.Unicode(length=32), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("username"),
    )
    op.create_index(op.f("ix_admin_accounts_id"), "admin_accounts", ["id"], unique=False)
    op.create_index(op.f("ix_admin_accounts_role"), "admin_accounts", ["role"], unique=False)
    op.create_index(op.f("ix_admin_accounts_username"), "admin_accounts", ["username"], unique=False)

def downgrade() -> None:
    op.drop_index(op.f("ix_admin_accounts_username"), table_name="admin_accounts")
    op.drop_index(op.f("ix_admin_accounts_role"), table_name="admin_accounts")
    op.drop_index(op.f("ix_admin_accounts_id"), table_name="admin_accounts")
    op.drop_table("admin_accounts")
    op.drop_column("users", "api_key_question_limit_daily")
    op.drop_column("users", "free_question_limit_daily")
