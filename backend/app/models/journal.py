"""决策日志与复盘模型。"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Column
from sqlalchemy.types import JSON
from sqlmodel import Field, SQLModel

from app.core.money import DecimalString
from app.models.base import utcnow


class Journal(SQLModel, table=True):
    """决策日志（journals 表）。

    提交后 is_locked=True，DB 中间件拦截后续 UPDATE（只能追加 review）。
    """

    __tablename__ = "journals"

    id: int | None = Field(default=None, primary_key=True)
    stock_id: int = Field(foreign_key="stocks.id", index=True)
    decision_type: str  # BUY / SELL / HOLD / WATCH
    # 结构化字段
    thesis_category: str | None = None  # VALUATION / TREND / EVENT / GROWTH / OTHER
    expected_horizon: str | None = None  # SHORT / MEDIUM / LONG
    target_price: Decimal | None = Field(default=None, sa_column=Column(DecimalString))
    stop_loss_price: Decimal | None = Field(default=None, sa_column=Column(DecimalString))
    exit_condition: str | None = None
    confidence: int | None = None  # 1-5
    emotion: str | None = None  # CALM / HESITANT / FOMO / PANIC / REVENGE
    # 自由文本
    thesis: str
    risks: str | None = None
    tags: list[str] | None = Field(default=None, sa_column=Column(JSON))
    # 锁定
    is_locked: bool = False
    is_imported: bool = False  # 导入占位日志，允许后期补写
    locked_at: datetime | None = None
    created_at: datetime = Field(default_factory=utcnow)


class Review(SQLModel, table=True):
    """事后复盘（reviews 表，INSERT 追加，不改 journal 本体）。"""

    __tablename__ = "reviews"

    id: int | None = Field(default=None, primary_key=True)
    journal_id: int = Field(foreign_key="journals.id", index=True)
    review_date: date
    days_since_decision: int | None = None
    price_at_review: Decimal | None = Field(default=None, sa_column=Column(DecimalString))
    pnl_pct: Decimal | None = Field(default=None, sa_column=Column(DecimalString))
    benchmark_pnl_pct: Decimal | None = Field(default=None, sa_column=Column(DecimalString))
    thesis_held: bool | None = None
    luck_vs_skill: str | None = None  # SKILL / LUCK / MIXED
    lessons: str | None = None
    notes: str | None = None
    created_at: datetime = Field(default_factory=utcnow)


__all__ = ["Journal", "Review"]
