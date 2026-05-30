"""财报与估值指标模型。"""

from __future__ import annotations

from datetime import date as date_type
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Column, UniqueConstraint
from sqlmodel import Field, SQLModel

from app.core.money import DecimalString
from app.models.base import utcnow


class Financial(SQLModel, table=True):
    """股票财务/估值快照（financials 表）。

    按 (stock_id, as_of) 唯一；估值类（pe/pb/roe）随时间变化，存多份快照。
    比率类字段用 DecimalString 存储（避免浮点），百分比以小数存（0.15 = 15%）。
    """

    __tablename__ = "financials"
    __table_args__ = (UniqueConstraint("stock_id", "as_of", name="uq_fin_stock_asof"),)

    id: int | None = Field(default=None, primary_key=True)
    stock_id: int = Field(foreign_key="stocks.id", index=True)
    as_of: date_type = Field(index=True)
    pe: Decimal | None = Field(default=None, sa_column=Column(DecimalString))
    pb: Decimal | None = Field(default=None, sa_column=Column(DecimalString))
    roe: Decimal | None = Field(default=None, sa_column=Column(DecimalString))  # TTM, 小数
    revenue_yoy: Decimal | None = Field(default=None, sa_column=Column(DecimalString))  # 小数
    profit_yoy: Decimal | None = Field(default=None, sa_column=Column(DecimalString))  # 小数
    market_cap: Decimal | None = Field(default=None, sa_column=Column(DecimalString))
    dividend_yield: Decimal | None = Field(default=None, sa_column=Column(DecimalString))
    eps: Decimal | None = Field(default=None, sa_column=Column(DecimalString))
    source: str | None = None
    created_at: datetime = Field(default_factory=utcnow)


__all__ = ["Financial"]
