"""AI 分析缓存模型。"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import Column
from sqlalchemy.types import JSON
from sqlmodel import Field, SQLModel

from app.core.money import DecimalString
from app.models.base import utcnow


class AiInsight(SQLModel, table=True):
    """AI 分析缓存（ai_insights 表）。"""

    __tablename__ = "ai_insights"

    id: int | None = Field(default=None, primary_key=True)
    target_type: str = Field(index=True)  # STOCK / TRANSACTION / JOURNAL / PORTFOLIO
    target_id: int | None = Field(default=None, index=True)
    prompt_type: str  # TRADE_REVIEW / EARNINGS_SUMMARY / ...
    input_hash: str = Field(index=True)
    model: str
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    cost_jpy: Decimal | None = Field(default=None, sa_column=Column(DecimalString))
    response: str
    meta: dict[str, Any] | None = Field(default=None, sa_column=Column("metadata", JSON))
    created_at: datetime = Field(default_factory=utcnow, index=True)


__all__ = ["AiInsight"]
