"""交易流水模型（仅买/卖）。"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Column
from sqlmodel import Field, SQLModel

from app.core.money import DecimalString
from app.models.base import utcnow


class Transaction(SQLModel, table=True):
    """交易流水（transactions 表，仅 BUY / SELL）。

    金额/数量/价格/汇率/费用全部用 DecimalString（TEXT）存储。
    """

    __tablename__ = "transactions"

    id: int | None = Field(default=None, primary_key=True)
    stock_id: int = Field(foreign_key="stocks.id", index=True)
    type: str  # BUY / SELL
    trade_date: date = Field(index=True)
    quantity: Decimal = Field(sa_column=Column(DecimalString, nullable=False))
    price: Decimal = Field(sa_column=Column(DecimalString, nullable=False))  # 原币种成交价
    currency: str
    fx_rate_to_jpy: Decimal | None = Field(default=None, sa_column=Column(DecimalString))
    commission: Decimal = Field(default=Decimal("0"), sa_column=Column(DecimalString))
    tax: Decimal = Field(default=Decimal("0"), sa_column=Column(DecimalString))
    other_fees: Decimal = Field(default=Decimal("0"), sa_column=Column(DecimalString))
    journal_id: int | None = Field(default=None, foreign_key="journals.id")
    is_imported: bool = False  # CSV 导入标记
    notes: str | None = None
    created_at: datetime = Field(default_factory=utcnow)


__all__ = ["Transaction"]
