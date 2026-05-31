"""add sync_settings table (daily auto-sync toggle)

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-05-31 17:00:00.000000

"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel  # noqa: F401

from alembic import op


revision: str = "e5f6a7b8c9d0"
down_revision: str | None = "d4e5f6a7b8c9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "sync_settings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("auto_sync_enabled", sa.Boolean(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    # 写入默认单份配置（id=1，默认开启自动同步）
    op.execute(
        "INSERT INTO sync_settings (id, auto_sync_enabled, updated_at) "
        "VALUES (1, 1, CURRENT_TIMESTAMP)"
    )


def downgrade() -> None:
    op.drop_table("sync_settings")
