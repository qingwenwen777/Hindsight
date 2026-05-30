"""关注列表模型。"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import Column
from sqlalchemy.types import JSON
from sqlmodel import Field, SQLModel

from app.models.base import utcnow


class Watchlist(SQLModel, table=True):
    """关注列表（watchlist 表）。每只股票最多一条。"""

    __tablename__ = "watchlist"

    id: int | None = Field(default=None, primary_key=True)
    stock_id: int = Field(foreign_key="stocks.id", unique=True, index=True)
    notes: str | None = None
    tags: list[str] | None = Field(default=None, sa_column=Column(JSON))
    added_at: datetime = Field(default_factory=utcnow)


__all__ = ["Watchlist"]
