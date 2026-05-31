"""行情同步设置（单用户全局单份，固定 id=1）。"""

from __future__ import annotations

from datetime import datetime

from sqlmodel import Field, SQLModel

from app.models.base import utcnow


class SyncSetting(SQLModel, table=True):
    """行情同步设置。

    控制"已录入股票每日自动更新"开关。调度任务每次运行前读取本表，
    关闭时跳过自动同步（仍可手动一键更新）。
    """

    __tablename__ = "sync_settings"

    id: int | None = Field(default=None, primary_key=True)
    # 是否启用每日自动同步已录入股票的行情
    auto_sync_enabled: bool = True
    updated_at: datetime = Field(default_factory=utcnow)


__all__ = ["SyncSetting"]
