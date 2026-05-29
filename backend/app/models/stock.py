"""股票元信息与日线行情模型。"""

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


class Stock(SQLModel, table=True):
    """股票元信息（stocks 表）。"""

    __tablename__ = "stocks"
    __table_args__ = (UniqueConstraint("symbol", "market", name="uq_stock_symbol_market"),)

    id: int | None = Field(default=None, primary_key=True)
    symbol: str = Field(index=True)  # '600519' / 'AAPL' / '0700.HK'
    market: str = Field(index=True)  # CN / US / HK / JP
    name: str
    name_en: str | None = None
    industry: str | None = Field(default=None, index=True)
    sector: str | None = None
    currency: str  # CNY / USD / HKD / JPY
    listed_date: date_type | None = None
    delisted_date: date_type | None = None
    is_etf: bool = False
    meta: dict[str, Any] | None = Field(default=None, sa_column=Column("metadata", JSON))
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class Price(SQLModel, table=True):
    """日线行情（prices 表，默认前复权）。

    金额列用 DecimalString（TEXT 存储）；volume 用 int。
    """

    __tablename__ = "prices"

    stock_id: int = Field(foreign_key="stocks.id", primary_key=True)
    date: date_type = Field(primary_key=True, index=True)
    open: Decimal | None = Field(default=None, sa_column=Column(DecimalString))
    high: Decimal | None = Field(default=None, sa_column=Column(DecimalString))
    low: Decimal | None = Field(default=None, sa_column=Column(DecimalString))
    close: Decimal = Field(sa_column=Column(DecimalString, nullable=False))
    volume: int | None = Field(default=None)
    turnover: Decimal | None = Field(default=None, sa_column=Column(DecimalString))
    adjust_factor: Decimal | None = Field(default=None, sa_column=Column(DecimalString))


__all__ = ["Stock", "Price"]
