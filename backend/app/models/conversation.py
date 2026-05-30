"""AI 对话持久化模型：会话 + 消息。"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import Column
from sqlalchemy.types import JSON
from sqlmodel import Field, SQLModel

from app.core.money import DecimalString
from app.models.base import utcnow


class Conversation(SQLModel, table=True):
    """一段 AI 对话会话（conversations 表）。"""

    __tablename__ = "conversations"

    id: int | None = Field(default=None, primary_key=True)
    title: str = Field(default="新对话")
    created_at: datetime = Field(default_factory=utcnow, index=True)
    updated_at: datetime = Field(default_factory=utcnow, index=True)


class ConversationMessage(SQLModel, table=True):
    """对话中的单条消息（conversation_messages 表）。"""

    __tablename__ = "conversation_messages"

    id: int | None = Field(default=None, primary_key=True)
    conversation_id: int = Field(foreign_key="conversations.id", index=True)
    role: str  # user / assistant
    content: str
    model: str | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    cost_jpy: Decimal | None = Field(default=None, sa_column=Column(DecimalString))
    cached: bool = False
    context_refs: list[dict[str, Any]] | None = Field(default=None, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=utcnow, index=True)


__all__ = ["Conversation", "ConversationMessage"]
