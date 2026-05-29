"""APScheduler 调度（设计文档 5.1 时间表，JST）。

本地默认不自动跑（可手动触发 /admin/sync）。要启用后台调度，
设置环境变量 ENABLE_SCHEDULER=true，在 app 启动时调用 start_scheduler。
"""

from __future__ import annotations

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlmodel import Session

from app.database import engine
from app.logging_config import get_logger
from app.services.data_sync.sync_service import sync_market_prices

log = get_logger(__name__)

_scheduler: BackgroundScheduler | None = None

# 调度时间表（JST）：market -> (hour, minute)
_SCHEDULE = {
    "CN": (16, 30),
    "HK": (17, 30),
    "US": (6, 30),  # 次日
    "JP": (16, 0),
}


def _run_market_sync(market: str) -> None:
    """调度任务：同步某市场。"""
    log.info("scheduler.sync_start", market=market)
    with Session(engine) as session:
        report = sync_market_prices(session, market)
    log.info(
        "scheduler.sync_done",
        market=market,
        inserted=report.total_inserted,
        failed=len(report.failed),
    )


def start_scheduler() -> BackgroundScheduler:
    """启动后台调度器（时区 Asia/Tokyo）。"""
    global _scheduler
    if _scheduler is not None:
        return _scheduler

    scheduler = BackgroundScheduler(timezone="Asia/Tokyo")
    for market, (hour, minute) in _SCHEDULE.items():
        scheduler.add_job(
            _run_market_sync,
            CronTrigger(hour=hour, minute=minute),
            args=[market],
            id=f"sync_{market}",
            replace_existing=True,
        )
    scheduler.start()
    _scheduler = scheduler
    log.info("scheduler.started", markets=list(_SCHEDULE.keys()))
    return scheduler


def shutdown_scheduler() -> None:
    """停止调度器。"""
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
