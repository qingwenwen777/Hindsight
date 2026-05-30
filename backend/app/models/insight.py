"""AI 洞察相关模型：文档 / 日报配置 / 筛选规则 / 价格提醒。"""

from __future__ import annotations

from datetime import date as date_type
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import Column, UniqueConstraint
from sqlalchemy.types import JSON
from sqlmodel import Field, SQLModel

from app.core.money import DecimalString
from app.models.base import utcnow


class InsightDocument(SQLModel, table=True):
    """AI 洞察文档（日报 / 筛选点评），Markdown 正文。"""

    __tablename__ = "insight_documents"
    __table_args__ = (
        UniqueConstraint("doc_type", "market", "report_date", name="uq_insight_daily"),
    )

    id: int | None = Field(default=None, primary_key=True)
    doc_type: str = Field(index=True)  # DAILY_REPORT | SCREENER_REVIEW
    market: str | None = Field(default=None, index=True)  # US/CN/HK/JP
    title: str
    body_md: str
    report_date: date_type | None = Field(default=None)  # 日报对应日期（按天去重）
    model: str | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    degraded: bool = False
    degraded_reason: str | None = None
    source_ref: dict[str, Any] | None = Field(default=None, sa_column=Column(JSON))
    is_read: bool = False
    created_at: datetime = Field(default_factory=utcnow, index=True)


class ReportConfig(SQLModel, table=True):
    """日报配置（单用户全局单份，固定 id=1）。"""

    __tablename__ = "report_configs"

    id: int | None = Field(default=None, primary_key=True)
    enabled_markets: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    schedule: dict[str, str] = Field(default_factory=dict, sa_column=Column(JSON))
    move_threshold_pct: Decimal = Field(
        default=Decimal("5"), sa_column=Column(DecimalString, nullable=False)
    )
    detail_level: str = "STANDARD"  # BRIEF | STANDARD | DETAILED
    tone: str = "NEUTRAL"  # CONSERVATIVE | NEUTRAL
    language: str = "zh"  # zh | ja | en（AI 正文语言）
    focus_text: str | None = None
    constraints: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    # 日报使用的 AI 服务商与模型（为空则用全局默认服务商）
    provider_id: int | None = Field(default=None, foreign_key="ai_providers.id")
    model_name: str | None = None
    updated_at: datetime = Field(default_factory=utcnow)


class ScreenerRule(SQLModel, table=True):
    """命名筛选规则。"""

    __tablename__ = "screener_rules"

    id: int | None = Field(default=None, primary_key=True)
    name: str
    conditions: list[dict[str, Any]] = Field(default_factory=list, sa_column=Column(JSON))
    markets: list[str] | None = Field(default=None, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class PriceAlert(SQLModel, table=True):
    """价格提醒（触及目标价/止损价）。"""

    __tablename__ = "price_alerts"

    id: int | None = Field(default=None, primary_key=True)
    stock_id: int = Field(foreign_key="stocks.id", index=True)
    journal_id: int | None = Field(default=None, foreign_key="journals.id")
    alert_type: str  # TARGET | STOP
    threshold: Decimal = Field(sa_column=Column(DecimalString, nullable=False))
    triggered_price: Decimal = Field(sa_column=Column(DecimalString, nullable=False))
    dedup_key: str = Field(index=True, unique=True)  # f"{stock_id}:{type}:{threshold}"
    is_read: bool = False
    triggered_at: datetime = Field(default_factory=utcnow, index=True)


__all__ = ["InsightDocument", "ReportConfig", "ScreenerRule", "PriceAlert"]
