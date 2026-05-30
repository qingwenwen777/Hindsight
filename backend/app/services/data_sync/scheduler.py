"""APScheduler 调度（设计文档 5.1 时间表，JST）。

本地默认不自动跑（可手动触发 /admin/sync）。要启用后台调度，
设置环境变量 ENABLE_SCHEDULER=true，在 app 启动时调用 start_scheduler。

调度任务：
- 各市场行情同步（同步后评估价格提醒）
- 各市场 AI 日报（按 ReportConfig.schedule，可配置）
- 每日洞察文档清理（保留 90 天）
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

# 行情同步时间表（JST）：market -> (hour, minute)
_SCHEDULE = {
    "CN": (16, 30),
    "HK": (17, 30),
    "US": (6, 30),  # 次日
    "JP": (16, 0),
}


def _run_market_sync(market: str) -> None:
    """调度任务：同步某市场，并在同步后评估价格提醒。"""
    log.info("scheduler.sync_start", market=market)
    with Session(engine) as session:
        report = sync_market_prices(session, market)
        # 同步后评估价格提醒
        try:
            from app.services.insights.price_alerts import evaluate_price_alerts

            new_alerts = evaluate_price_alerts(session)
            if new_alerts:
                log.info("scheduler.price_alerts", market=market, new=len(new_alerts))
        except Exception as e:  # noqa: BLE001
            log.warning("scheduler.price_alerts_failed", market=market, error=str(e))
    log.info(
        "scheduler.sync_done",
        market=market,
        inserted=report.total_inserted,
        failed=len(report.failed),
    )


def _run_daily_report(market: str) -> None:
    """调度任务：生成某市场 AI 日报。"""
    log.info("scheduler.report_start", market=market)
    try:
        with Session(engine) as session:
            from app.services.insights.daily_report import build_daily_report

            doc = build_daily_report(session, market)
            log.info("scheduler.report_done", market=market, doc_id=doc.id, degraded=doc.degraded)
    except Exception as e:  # noqa: BLE001
        log.warning("scheduler.report_failed", market=market, error=str(e))


def _run_cleanup() -> None:
    """调度任务：清理超 90 天的洞察文档。"""
    try:
        with Session(engine) as session:
            from app.services.insights.cleanup import purge_old_documents

            n = purge_old_documents(session, days=90)
            log.info("scheduler.cleanup_done", purged=n)
    except Exception as e:  # noqa: BLE001
        log.warning("scheduler.cleanup_failed", error=str(e))


def _parse_hhmm(value: str) -> tuple[int, int] | None:
    """'06:30' -> (6, 30)。非法返回 None。"""
    try:
        hh, mm = value.split(":")
        return int(hh), int(mm)
    except (ValueError, AttributeError):
        return None


def _register_report_jobs(scheduler: BackgroundScheduler) -> None:
    """按 ReportConfig 注册各市场日报 job（先清除旧的同前缀 job）。"""
    # 清除已有日报 job
    for job in scheduler.get_jobs():
        if job.id and job.id.startswith("report_"):
            scheduler.remove_job(job.id)

    try:
        with Session(engine) as session:
            from app.services.insights.daily_report import get_or_create_config

            cfg = get_or_create_config(session)
            enabled = cfg.enabled_markets or []
            schedule = cfg.schedule or {}
    except Exception as e:  # noqa: BLE001
        log.warning("scheduler.report_config_failed", error=str(e))
        return

    for market in enabled:
        hhmm = _parse_hhmm(schedule.get(market, ""))
        if hhmm is None:
            continue
        hour, minute = hhmm
        scheduler.add_job(
            _run_daily_report,
            CronTrigger(hour=hour, minute=minute),
            args=[market],
            id=f"report_{market}",
            replace_existing=True,
        )
    log.info("scheduler.report_jobs", markets=enabled)


def reschedule_reports() -> None:
    """配置变更后重排日报 job（调度未启用则静默跳过）。"""
    if _scheduler is None:
        return
    _register_report_jobs(_scheduler)


def start_scheduler() -> BackgroundScheduler:
    """启动后台调度器（时区 Asia/Tokyo）。"""
    global _scheduler
    if _scheduler is not None:
        return _scheduler

    scheduler = BackgroundScheduler(timezone="Asia/Tokyo")

    # 行情同步
    for market, (hour, minute) in _SCHEDULE.items():
        scheduler.add_job(
            _run_market_sync,
            CronTrigger(hour=hour, minute=minute),
            args=[market],
            id=f"sync_{market}",
            replace_existing=True,
        )

    # 每日清理（凌晨 4:00 JST）
    scheduler.add_job(
        _run_cleanup,
        CronTrigger(hour=4, minute=0),
        id="cleanup_insights",
        replace_existing=True,
    )

    scheduler.start()
    _scheduler = scheduler

    # 日报 job（依赖配置，启动后注册）
    _register_report_jobs(scheduler)

    log.info("scheduler.started", markets=list(_SCHEDULE.keys()))
    return scheduler


def shutdown_scheduler() -> None:
    """停止调度器。"""
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
