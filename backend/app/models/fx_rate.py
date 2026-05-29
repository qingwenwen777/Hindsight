"""汇率模型。"""

from __future__ import annotations

from datetime import date as date_type
from decimal import Decimal

from sqlalchemy import Column
from sqlmodel import Field, SQLModel

from app.core.money import DecimalString


class FxRate(SQLModel, table=True):
    """汇率（fx_rates 表）。rate 表示 1 单位 base = rate 单位 quote。"""

    __tablename__ = "fx_rates"

    date: date_type = Field(primary_key=True, index=True)
    base_currency: str = Field(primary_key=True)
    quote_currency: str = Field(primary_key=True)
    rate: Decimal = Field(sa_column=Column(DecimalString, nullable=False))


__all__ = ["FxRate"]
