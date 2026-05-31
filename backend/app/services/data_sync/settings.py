"""行情同步设置读写（单份，固定 id=1）。"""

from __future__ import annotations

from sqlmodel import Session

from app.models.sync_setting import SyncSetting


def get_or_create_sync_setting(session: Session) -> SyncSetting:
    """取同步设置（单份，id=1）；不存在则用默认值创建。"""
    setting = session.get(SyncSetting, 1)
    if setting is not None:
        return setting
    setting = SyncSetting(id=1, auto_sync_enabled=True)
    session.add(setting)
    session.commit()
    session.refresh(setting)
    return setting


__all__ = ["get_or_create_sync_setting"]
