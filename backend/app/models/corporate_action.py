"""公司行动模型（拆股/送股/配股/合并）。"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Column
from sqlmodel import Field, SQLModel

from app.core.money import DecimalString
from app.models.base import utcnow


class CorporateAction(SQLModel, table=True):
    """公司行动（corporate_actions 表）。

    拆股/送股：持股数乘以 ratio_num/ratio_den（如 10 送 10 = 2/1）。
    配股：按 subscribe_ratio 比例可认购，认购价 subscribe_price。
    """

    __tablename__ = "corporate_actions"

    id: int | None = Field(default=None, primary_key=True)
    stock_id: int = Field(foreign_key="stocks.id", index=True)
    action_type: str  # SPLIT / BONUS / RIGHTS / MERGE
    ex_date: date = Field(index=True)  # 除权除息日
    ratio_num: Decimal | None = Field(default=None, sa_column=Column(DecimalString))
    ratio_den: Decimal | None = Field(default=None, sa_column=Column(DecimalString))
    subscribe_ratio: Decimal | None = Field(default=None, sa_column=Column(DecimalString))
    subscribe_price: Decimal | None = Field(default=None, sa_column=Column(DecimalString))
    notes: str | None = None
    created_at: datetime = Field(default_factory=utcnow)


__all__ = ["CorporateAction"]
