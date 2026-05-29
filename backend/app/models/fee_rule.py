"""手续费规则模型（版本化，按交易日匹配生效规则）。"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import Column
from sqlmodel import Field, SQLModel

from app.core.money import DecimalString


class FeeRule(SQLModel, table=True):
    """手续费规则（fee_rules 表）。

    费率随政策变动（如 A 股印花税历史调整），用 effective_from/to 版本化。
    rate / min_amount / fixed_amount 用 DecimalString 存储。
    """

    __tablename__ = "fee_rules"

    id: int | None = Field(default=None, primary_key=True)
    market: str = Field(index=True)  # CN / US / HK / JP
    broker: str | None = None
    direction: str | None = None  # BUY / SELL / BOTH
    fee_type: str  # COMMISSION / STAMP / SEC_FEE / TRANSFER / FINRA / ...
    rate: Decimal | None = Field(default=None, sa_column=Column(DecimalString))
    min_amount: Decimal | None = Field(default=None, sa_column=Column(DecimalString))
    fixed_amount: Decimal | None = Field(default=None, sa_column=Column(DecimalString))
    # 每股固定费（如 FINRA per-share），用 DecimalString
    per_share: Decimal | None = Field(default=None, sa_column=Column(DecimalString))
    effective_from: date
    effective_to: date | None = None


__all__ = ["FeeRule"]
