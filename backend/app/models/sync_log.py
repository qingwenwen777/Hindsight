"""同步日志模型 —— 记录每次行情同步的结果与失败原因。"""

from __future__ import annotations

from datetime import datetime

from sqlmodel import Field, SQLModel

from app.models.base import utcnow


class SyncLog(SQLModel, table=True):
    """行情同步日志（sync_logs 表）。"""

    __tablename__ = "sync_logs"

    id: int | None = Field(default=None, primary_key=True)
    market: str = Field(index=True)
    symbol: str | None = None
    source: str | None = None  # akshare / yfinance / ...
    ok: bool = True
    inserted: int = 0
    updated: int = 0
    skipped: int = 0
    message: str | None = None
    created_at: datetime = Field(default_factory=utcnow, index=True)


__all__ = ["SyncLog"]
