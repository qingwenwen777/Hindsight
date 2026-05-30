"""add report_jobs table (async daily report generation tracking)

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-05-31 15:00:00.000000

"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel  # noqa: F401

from alembic import op


revision: str = "d4e5f6a7b8c9"
down_revision: str | None = "c3d4e5f6a7b8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "report_jobs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("market", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("status", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("stage", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("progress", sa.Integer(), nullable=False),
        sa.Column("message", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("document_id", sa.Integer(), nullable=True),
        sa.Column("degraded", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["document_id"], ["insight_documents.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("report_jobs", schema=None) as batch_op:
        batch_op.create_index("ix_report_jobs_market", ["market"], unique=False)
        batch_op.create_index("ix_report_jobs_status", ["status"], unique=False)
        batch_op.create_index("ix_report_jobs_created_at", ["created_at"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("report_jobs", schema=None) as batch_op:
        batch_op.drop_index("ix_report_jobs_created_at")
        batch_op.drop_index("ix_report_jobs_status")
        batch_op.drop_index("ix_report_jobs_market")
    op.drop_table("report_jobs")
