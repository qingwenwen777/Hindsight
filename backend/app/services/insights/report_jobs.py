"""日报生成任务服务 —— 创建任务、后台执行（带进度上报）、查询状态。

设计：
- 任务状态落库（ReportJob），前端可轮询，实现"可感知的异步生成"。
- 并发保护：同一市场已有 PENDING/RUNNING 任务时，复用该任务而非重复入队。
- 后台执行用独立 Session，逐阶段更新 stage/progress/message。
"""

from __future__ import annotations

from datetime import datetime, timedelta

from sqlmodel import Session, select

from app.database import engine
from app.logging_config import get_logger
from app.models.base import utcnow
from app.models.report_job import (
    JOB_FAILED,
    JOB_PENDING,
    JOB_RUNNING,
    JOB_SUCCESS,
    STAGE_DONE,
    STAGE_QUEUED,
    ReportJob,
)
from app.services.insights.daily_report import build_daily_report

log = get_logger(__name__)

# 活跃状态（用于并发去重）
_ACTIVE = (JOB_PENDING, JOB_RUNNING)
# 任务被视为"卡死"的超时阈值（分钟）；超过则允许重新入队
_STALE_MINUTES = 10


def find_active_job(session: Session, market: str) -> ReportJob | None:
    """查找某市场仍在进行（未超时）的任务。"""
    market = market.upper()
    rows = session.exec(
        select(ReportJob)
        .where(ReportJob.market == market, ReportJob.status.in_(_ACTIVE))  # type: ignore[attr-defined]
        .order_by(ReportJob.created_at.desc())
    ).all()
    cutoff = utcnow() - timedelta(minutes=_STALE_MINUTES)
    for job in rows:
        updated = job.updated_at
        # SQLite 存的是 naive UTC，统一去掉 tzinfo 比较
        if updated is not None and updated.tzinfo is not None:
            updated = updated.replace(tzinfo=None)
        ref = cutoff.replace(tzinfo=None)
        if updated is not None and updated >= ref:
            return job
    return None


def create_job(session: Session, market: str) -> tuple[ReportJob, bool]:
    """创建一个待执行任务。返回 (job, created)。

    若该市场已有进行中的任务，则复用它（created=False），避免重复生成。
    """
    market = market.upper()
    existing = find_active_job(session, market)
    if existing is not None:
        return existing, False

    job = ReportJob(
        market=market,
        status=JOB_PENDING,
        stage=STAGE_QUEUED,
        progress=0,
        message="排队中",
    )
    session.add(job)
    session.commit()
    session.refresh(job)
    return job, True


def _update(
    session: Session,
    job_id: int,
    *,
    status: str | None = None,
    stage: str | None = None,
    progress: int | None = None,
    message: str | None = None,
    document_id: int | None = None,
    degraded: bool | None = None,
    finished: bool = False,
) -> None:
    """更新任务字段（每次都 commit，保证前端轮询能读到最新进度）。"""
    job = session.get(ReportJob, job_id)
    if job is None:
        return
    if status is not None:
        job.status = status
    if stage is not None:
        job.stage = stage
    if progress is not None:
        job.progress = progress
    if message is not None:
        job.message = message
    if document_id is not None:
        job.document_id = document_id
    if degraded is not None:
        job.degraded = degraded
    job.updated_at = utcnow()
    if finished:
        job.finished_at = utcnow()
    session.add(job)
    session.commit()


def run_job(job_id: int) -> None:
    """后台执行任务：调用日报生成，逐阶段上报进度。独立 Session。"""
    with Session(engine) as session:
        job = session.get(ReportJob, job_id)
        if job is None:
            log.warning("report_job.missing", job_id=job_id)
            return
        market = job.market
        _update(
            session, job_id,
            status=JOB_RUNNING, stage="CONTEXT", progress=5, message="开始生成",
        )

        def _reporter(stage: str, progress: int, message: str | None = None) -> None:
            _update(session, job_id, stage=stage, progress=progress, message=message)

        try:
            doc = build_daily_report(session, market, progress=_reporter)
            _update(
                session, job_id,
                status=JOB_SUCCESS, stage=STAGE_DONE, progress=100,
                message="降级生成（数据汇总版）" if doc.degraded else "生成完成",
                document_id=doc.id, degraded=doc.degraded, finished=True,
            )
            log.info("report_job.done", job_id=job_id, market=market, doc_id=doc.id, degraded=doc.degraded)
        except Exception as e:  # noqa: BLE001 — 任何失败都要写回任务状态，前端可见
            log.warning("report_job.failed", job_id=job_id, market=market, error=str(e))
            _update(
                session, job_id,
                status=JOB_FAILED, stage=STAGE_DONE, progress=100,
                message=f"生成失败：{e}", finished=True,
            )


def get_job(session: Session, job_id: int) -> ReportJob | None:
    return session.get(ReportJob, job_id)


def latest_jobs(session: Session, limit: int = 20) -> list[ReportJob]:
    return list(
        session.exec(
            select(ReportJob).order_by(ReportJob.created_at.desc()).limit(limit)
        ).all()
    )


__all__ = ["create_job", "run_job", "get_job", "latest_jobs", "find_active_job"]
