"""add conversations and conversation_messages

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-05-30 20:00:00.000000

"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel  # noqa: F401
from sqlalchemy.dialects import sqlite

import app.core.money  # noqa: F401  DecimalString 自定义类型

from alembic import op


revision: str = "b2c3d4e5f6a7"
down_revision: str | None = "a1b2c3d4e5f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "conversations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("conversations", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_conversations_created_at"), ["created_at"], unique=False)
        batch_op.create_index(batch_op.f("ix_conversations_updated_at"), ["updated_at"], unique=False)

    op.create_table(
        "conversation_messages",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("conversation_id", sa.Integer(), nullable=False),
        sa.Column("role", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("content", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("model", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("prompt_tokens", sa.Integer(), nullable=True),
        sa.Column("completion_tokens", sa.Integer(), nullable=True),
        sa.Column("cost_jpy", app.core.money.DecimalString(), nullable=True),
        sa.Column("cached", sa.Boolean(), nullable=False),
        sa.Column("context_refs", sqlite.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("conversation_messages", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_conversation_messages_conversation_id"), ["conversation_id"], unique=False
        )
        batch_op.create_index(
            batch_op.f("ix_conversation_messages_created_at"), ["created_at"], unique=False
        )


def downgrade() -> None:
    with op.batch_alter_table("conversation_messages", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_conversation_messages_created_at"))
        batch_op.drop_index(batch_op.f("ix_conversation_messages_conversation_id"))
    op.drop_table("conversation_messages")
    with op.batch_alter_table("conversations", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_conversations_updated_at"))
        batch_op.drop_index(batch_op.f("ix_conversations_created_at"))
    op.drop_table("conversations")
