"""现金账户与现金流模型。"""

from __future__ import annotations

from datetime import date as date_type
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Column
from sqlmodel import Field, SQLModel

from app.core.money import DecimalString
from app.models.base import utcnow


class CashAccount(SQLModel, table=True):
    """现金账户（cash_accounts 表）。"""

    __tablename__ = "cash_accounts"

    id: int | None = Field(default=None, primary_key=True)
    name: str  # '富途港股' / 'IBKR 美股'
    broker: str | None = None
    currency: str
    notes: str | None = None
    created_at: datetime = Field(default_factory=utcnow)


class CashFlow(SQLModel, table=True):
    """现金流（cash_flows 表）。amount 正=入、负=出。"""

    __tablename__ = "cash_flows"

    id: int | None = Field(default=None, primary_key=True)
    account_id: int = Field(foreign_key="cash_accounts.id", index=True)
    flow_date: date_type = Field(index=True)
    type: str  # DEPOSIT/WITHDRAW/DIVIDEND/INTEREST/TRADE_BUY/TRADE_SELL/FEE/TAX/FX
    amount: Decimal = Field(sa_column=Column(DecimalString, nullable=False))
    currency: str
    fx_rate_to_jpy: Decimal | None = Field(default=None, sa_column=Column(DecimalString))
    related_tx_id: int | None = Field(default=None, foreign_key="transactions.id")
    notes: str | None = None
    created_at: datetime = Field(default_factory=utcnow)


__all__ = ["CashAccount", "CashFlow"]
