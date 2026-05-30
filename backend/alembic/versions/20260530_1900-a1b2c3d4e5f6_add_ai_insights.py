"""add ai insights (documents, report config, screener rules, price alerts)

Revision ID: a1b2c3d4e5f6
Revises: 2dbf9657097c
Create Date: 2026-05-30 19:00:00.000000

"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel  # noqa: F401
from sqlalchemy.dialects import sqlite

import app.core.money  # noqa: F401  DecimalString 自定义类型

from alembic import op


revision: str = "a1b2c3d4e5f6"
down_revision: str | None = "2dbf9657097c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "insight_documents",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("doc_type", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("market", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("title", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("body_md", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("report_date", sa.Date(), nullable=True),
        sa.Column("model", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("prompt_tokens", sa.Integer(), nullable=True),
        sa.Column("completion_tokens", sa.Integer(), nullable=True),
        sa.Column("degraded", sa.Boolean(), nullable=False),
        sa.Column("degraded_reason", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("source_ref", sqlite.JSON(), nullable=True),
        sa.Column("is_read", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("doc_type", "market", "report_date", name="uq_insight_daily"),
    )
    with op.batch_alter_table("insight_documents", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_insight_documents_doc_type"), ["doc_type"], unique=False)
        batch_op.create_index(batch_op.f("ix_insight_documents_market"), ["market"], unique=False)
        batch_op.create_index(batch_op.f("ix_insight_documents_created_at"), ["created_at"], unique=False)

    op.create_table(
        "report_configs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("enabled_markets", sqlite.JSON(), nullable=True),
        sa.Column("schedule", sqlite.JSON(), nullable=True),
        sa.Column("move_threshold_pct", app.core.money.DecimalString(), nullable=False),
        sa.Column("detail_level", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("tone", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("language", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("focus_text", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("constraints", sqlite.JSON(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "screener_rules",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("conditions", sqlite.JSON(), nullable=True),
        sa.Column("markets", sqlite.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "price_alerts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("stock_id", sa.Integer(), nullable=False),
        sa.Column("journal_id", sa.Integer(), nullable=True),
        sa.Column("alert_type", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("threshold", app.core.money.DecimalString(), nullable=False),
        sa.Column("triggered_price", app.core.money.DecimalString(), nullable=False),
        sa.Column("dedup_key", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("is_read", sa.Boolean(), nullable=False),
        sa.Column("triggered_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["stock_id"], ["stocks.id"]),
        sa.ForeignKeyConstraint(["journal_id"], ["journals.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("price_alerts", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_price_alerts_stock_id"), ["stock_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_price_alerts_dedup_key"), ["dedup_key"], unique=True)
        batch_op.create_index(batch_op.f("ix_price_alerts_triggered_at"), ["triggered_at"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("price_alerts", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_price_alerts_triggered_at"))
        batch_op.drop_index(batch_op.f("ix_price_alerts_dedup_key"))
        batch_op.drop_index(batch_op.f("ix_price_alerts_stock_id"))
    op.drop_table("price_alerts")
    op.drop_table("screener_rules")
    op.drop_table("report_configs")
    with op.batch_alter_table("insight_documents", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_insight_documents_created_at"))
        batch_op.drop_index(batch_op.f("ix_insight_documents_market"))
        batch_op.drop_index(batch_op.f("ix_insight_documents_doc_type"))
    op.drop_table("insight_documents")
