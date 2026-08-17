"""add single-user persistent memories

Revision ID: 20260817_0006
Revises: 20260718_0005
Create Date: 2026-08-17
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260817_0006"
down_revision = "20260718_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "memories",
        sa.Column(
            "id",
            sa.Uuid(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("subject", sa.Unicode(length=30), nullable=False),
        sa.Column("memory_key", sa.Unicode(length=150), nullable=False),
        sa.Column("memory_value", sa.Text(), nullable=False),
        sa.Column("memory_type", sa.Unicode(length=30), nullable=False),
        sa.Column(
            "importance",
            sa.Float(),
            server_default=sa.text("0.5"),
            nullable=False,
        ),
        sa.Column(
            "confidence",
            sa.Float(),
            server_default=sa.text("1.0"),
            nullable=False,
        ),
        sa.Column("source_message_id", sa.Uuid(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            server_default=sa.text("TRUE"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "importance >= 0.0 AND importance <= 1.0",
            name="ck_memories_importance_range",
        ),
        sa.CheckConstraint(
            "confidence >= 0.0 AND confidence <= 1.0",
            name="ck_memories_confidence_range",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "subject",
            "memory_key",
            name="uq_memories_subject_key",
        ),
    )
    op.create_index("ix_memories_subject", "memories", ["subject"])
    op.create_index("ix_memories_memory_type", "memories", ["memory_type"])
    op.create_index("ix_memories_is_active", "memories", ["is_active"])
    op.create_index("ix_memories_expires_at", "memories", ["expires_at"])

    op.execute(
        """
        CREATE OR REPLACE FUNCTION public.friday_memories_set_updated_at()
        RETURNS TRIGGER
        LANGUAGE plpgsql
        AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_memories_set_updated_at
        BEFORE UPDATE ON public.memories
        FOR EACH ROW
        EXECUTE FUNCTION public.friday_memories_set_updated_at()
        """
    )
    op.execute("ALTER TABLE public.memories ENABLE ROW LEVEL SECURITY")
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
                EXECUTE 'REVOKE ALL PRIVILEGES ON TABLE public.memories FROM anon';
            END IF;
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
                EXECUTE 'REVOKE ALL PRIVILEGES ON TABLE public.memories FROM authenticated';
            END IF;
        END;
        $$
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_memories_set_updated_at ON public.memories")
    op.drop_index("ix_memories_expires_at", table_name="memories")
    op.drop_index("ix_memories_is_active", table_name="memories")
    op.drop_index("ix_memories_memory_type", table_name="memories")
    op.drop_index("ix_memories_subject", table_name="memories")
    op.drop_table("memories")
    op.execute("DROP FUNCTION IF EXISTS public.friday_memories_set_updated_at()")
