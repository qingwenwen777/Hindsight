"""洞察文档保留策略 —— 清理超过 N 天的文档。"""

from __future__ import annotations

from datetime import timedelta

from sqlmodel import Session, delete, select

from app.logging_config import get_logger
from app.models.base import utcnow
from app.models.insight import InsightDocument

log = get_logger(__name__)


def purge_old_documents(session: Session, days: int = 90) -> int:
    """删除创建时间早于 now-days 的文档，返回删除条数。"""
    cutoff = utcnow() - timedelta(days=days)
    ids = session.exec(
        select(InsightDocument.id).where(InsightDocument.created_at < cutoff)
    ).all()
    count = len(ids)
    if count:
        session.exec(delete(InsightDocument).where(InsightDocument.created_at < cutoff))
        session.commit()
        log.info("insights.purged", count=count, days=days)
    return count


__all__ = ["purge_old_documents"]
