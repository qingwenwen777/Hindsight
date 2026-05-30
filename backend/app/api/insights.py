"""AI 洞察 API：文档列表/详情/下载/已读、日报配置、手动生成。"""

from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from sqlmodel import Session, select

from app.core.money import D, to_db_str
from app.core.response import Meta, ok
from app.database import engine, get_session
from app.logging_config import get_logger
from app.models.insight import InsightDocument, ReportConfig
from app.services.insights.daily_report import build_daily_report, get_or_create_config

router = APIRouter(prefix="/insights", tags=["insights"])
log = get_logger(__name__)


def _doc_brief(d: InsightDocument) -> dict:
    return {
        "id": d.id,
        "doc_type": d.doc_type,
        "market": d.market,
        "title": d.title,
        "report_date": d.report_date.isoformat() if d.report_date else None,
        "degraded": d.degraded,
        "is_read": d.is_read,
        "model": d.model,
        "created_at": d.created_at.isoformat() if d.created_at else None,
    }


@router.get("/documents", summary="洞察文档列表")
def list_documents(
    type: str | None = Query(None, description="DAILY_REPORT / SCREENER_REVIEW"),
    market: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session: Session = Depends(get_session),
) -> dict:
    stmt = select(InsightDocument)
    count_stmt = select(InsightDocument)
    if type:
        stmt = stmt.where(InsightDocument.doc_type == type.upper())
        count_stmt = count_stmt.where(InsightDocument.doc_type == type.upper())
    if market:
        stmt = stmt.where(InsightDocument.market == market.upper())
        count_stmt = count_stmt.where(InsightDocument.market == market.upper())
    total = len(list(session.exec(count_stmt).all()))
    stmt = stmt.order_by(InsightDocument.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    rows = list(session.exec(stmt).all())
    return ok(
        [_doc_brief(d) for d in rows],
        meta=Meta(page=page, page_size=page_size, total=total),
    )


@router.get("/unread-count", summary="未读洞察数")
def unread_count(session: Session = Depends(get_session)) -> dict:
    rows = session.exec(select(InsightDocument).where(InsightDocument.is_read == False)).all()  # noqa: E712
    return ok({"count": len(rows)})


@router.get("/documents/{doc_id}", summary="洞察文档详情")
def get_document(doc_id: int, session: Session = Depends(get_session)) -> dict:
    doc = session.get(InsightDocument, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")
    return ok(
        {
            **_doc_brief(doc),
            "body_md": doc.body_md,
            "degraded_reason": doc.degraded_reason,
            "prompt_tokens": doc.prompt_tokens,
            "completion_tokens": doc.completion_tokens,
            "source_ref": doc.source_ref,
        }
    )


@router.get("/documents/{doc_id}/download", summary="下载为 .md")
def download_document(doc_id: int, session: Session = Depends(get_session)):  # noqa: ANN201
    doc = session.get(InsightDocument, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")
    parts = [doc.doc_type.lower()]
    if doc.market:
        parts.append(doc.market)
    if doc.report_date:
        parts.append(doc.report_date.isoformat())
    else:
        parts.append(str(doc.id))
    filename = "-".join(parts) + ".md"
    return PlainTextResponse(
        doc.body_md,
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/documents/{doc_id}/read", summary="标记已读")
def mark_read(doc_id: int, session: Session = Depends(get_session)) -> dict:
    doc = session.get(InsightDocument, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")
    doc.is_read = True
    session.add(doc)
    session.commit()
    return ok({"id": doc_id, "is_read": True})


# ---- 日报配置 ----


class ReportConfigPayload(BaseModel):
    enabled_markets: list[str] | None = None
    schedule: dict[str, str] | None = None
    move_threshold_pct: str | None = None
    detail_level: str | None = None
    tone: str | None = None
    language: str | None = None
    focus_text: str | None = None
    constraints: list[str] | None = None
    provider_id: int | None = None
    model_name: str | None = None


def _config_dict(cfg: ReportConfig) -> dict:
    return {
        "enabled_markets": cfg.enabled_markets,
        "schedule": cfg.schedule,
        "move_threshold_pct": to_db_str(cfg.move_threshold_pct),
        "detail_level": cfg.detail_level,
        "tone": cfg.tone,
        "language": cfg.language,
        "focus_text": cfg.focus_text,
        "constraints": cfg.constraints,
        "provider_id": cfg.provider_id,
        "model_name": cfg.model_name,
        "updated_at": cfg.updated_at.isoformat() if cfg.updated_at else None,
    }


@router.get("/config", summary="日报配置")
def get_config(session: Session = Depends(get_session)) -> dict:
    return ok(_config_dict(get_or_create_config(session)))


@router.put("/config", summary="更新日报配置")
def update_config(payload: ReportConfigPayload, session: Session = Depends(get_session)) -> dict:
    from app.models.base import utcnow

    cfg = get_or_create_config(session)
    if payload.enabled_markets is not None:
        cfg.enabled_markets = [m.upper() for m in payload.enabled_markets]
    if payload.schedule is not None:
        cfg.schedule = payload.schedule
    if payload.move_threshold_pct is not None:
        cfg.move_threshold_pct = D(payload.move_threshold_pct)
    if payload.detail_level is not None:
        cfg.detail_level = payload.detail_level
    if payload.tone is not None:
        cfg.tone = payload.tone
    if payload.language is not None:
        cfg.language = payload.language
    if payload.focus_text is not None:
        cfg.focus_text = payload.focus_text
    if payload.constraints is not None:
        cfg.constraints = payload.constraints
    # provider_id / model_name：用 fields_set 判断是否传入（None 是合法值＝用默认）
    fields_set = payload.model_fields_set
    if "provider_id" in fields_set:
        cfg.provider_id = payload.provider_id
    if "model_name" in fields_set:
        cfg.model_name = payload.model_name or None
    cfg.updated_at = utcnow()
    session.add(cfg)
    session.commit()
    session.refresh(cfg)

    # 配置变更后尝试重排调度（未启用调度则静默跳过）
    try:
        from app.services.data_sync.scheduler import reschedule_reports

        reschedule_reports()
    except Exception as e:  # noqa: BLE001
        log.warning("insights.reschedule_skipped", error=str(e))

    return ok(_config_dict(cfg))


def _generate_task(market: str) -> None:
    """后台任务：生成日报（独立 session）。"""
    try:
        with Session(engine) as session:
            build_daily_report(session, market)
    except Exception as e:  # noqa: BLE001
        log.warning("insights.generate_failed", market=market, error=str(e))


def _job_dict(job) -> dict:  # noqa: ANN001
    """序列化任务状态。"""
    return {
        "id": job.id,
        "market": job.market,
        "status": job.status,
        "stage": job.stage,
        "progress": job.progress,
        "message": job.message,
        "document_id": job.document_id,
        "degraded": job.degraded,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "updated_at": job.updated_at.isoformat() if job.updated_at else None,
        "finished_at": job.finished_at.isoformat() if job.finished_at else None,
    }


@router.post("/daily/generate", summary="手动生成日报（异步任务）")
def generate_daily(
    market: str = Query(..., description="US/CN/HK/JP"),
    background_tasks: BackgroundTasks = None,  # type: ignore[assignment]
    session: Session = Depends(get_session),
) -> dict:
    """创建一个日报生成任务并在后台执行，立即返回任务状态供前端轮询。

    并发保护：同一市场已有进行中的任务则复用，不重复生成。
    """
    from app.services.insights.report_jobs import create_job, run_job

    market = market.upper()
    if market not in ("US", "CN", "HK", "JP"):
        raise HTTPException(status_code=422, detail="未知市场")

    job, created = create_job(session, market)
    if created:
        background_tasks.add_task(run_job, job.id)
    return ok(_job_dict(job), message="已入队" if created else "已有进行中的任务")


@router.get("/daily/jobs/{job_id}", summary="查询日报生成任务状态")
def get_job_status(job_id: int, session: Session = Depends(get_session)) -> dict:
    from app.services.insights.report_jobs import get_job

    job = get_job(session, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    return ok(_job_dict(job))


@router.get("/daily/jobs", summary="日报生成任务列表（最近）")
def list_jobs(session: Session = Depends(get_session)) -> dict:
    from app.services.insights.report_jobs import latest_jobs

    jobs = latest_jobs(session, limit=20)
    return ok([_job_dict(j) for j in jobs])


@router.delete("/documents/{doc_id}", summary="删除洞察文档")
def delete_document(doc_id: int, session: Session = Depends(get_session)) -> dict:
    """删除一篇洞察文档（日报/筛选点评）。

    解除关联任务对该文档的引用（置空 document_id），避免悬挂外键。
    """
    from app.models.report_job import ReportJob

    doc = session.get(InsightDocument, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")

    # 解除任务对该文档的引用
    jobs = session.exec(
        select(ReportJob).where(ReportJob.document_id == doc_id)
    ).all()
    for j in jobs:
        j.document_id = None
        session.add(j)

    session.delete(doc)
    session.commit()
    return ok({"deleted": doc_id})
