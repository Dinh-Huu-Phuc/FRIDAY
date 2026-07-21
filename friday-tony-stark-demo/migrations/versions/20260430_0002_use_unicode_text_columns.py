"""use unicode text columns

Revision ID: 20260430_0002
Revises: 20260429_0001
Create Date: 2026-04-30
"""
from __future__ import annotations

revision = "20260430_0002"
down_revision = "20260429_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # PostgreSQL VARCHAR and TEXT are Unicode-native, so no schema change is needed.
    pass


def downgrade() -> None:
    pass
