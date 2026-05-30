"""日报异步生成任务测试：创建/去重、后台执行进度、状态查询、文档删除。"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlmodel import Session, select

from app.models.insight import InsightDocument
from app.models.report_job import (
    JOB_PENDING,
    JOB_SUCCESS,
    ReportJob,
)
from app.models.stock import Price, Stock
from app.models.watchlist import Watchlist


def _stock(session: Session, symbol="AAPL", market="US") -> int:
    s = Stock(symbol=symbol, market=market, name=symbol, currency="USD")
    session.add(s)
    session.commit()
    session.refresh(s)
    return s.id


def _price(session: Session, sid: int, d: date, close: str) -> None:
    session.add(Price(stock_id=sid, date=d, close=Decimal(close)))
    session.commit()


def test_create_job_dedup(session: Session) -> None:
    """同市场已有进行中任务时复用，不重复入队。"""
    from app.services.insights.report_jobs import create_job

    job1, created1 = create_job(session, "US")
    assert created1 is True
    assert job1.status == JOB_PENDING

    job2, created2 = create_job(session, "US")
    assert created2 is False
    assert job2.id == job1.id

    # 不同市场互不影响
    job3, created3 = create_job(session, "JP")
    assert created3 is True
    assert job3.id != job1.id


def test_run_job_end_to_end_degraded(session: Session, engine, monkeypatch) -> None:
    """后台执行任务：无 AI → 降级成功，进度到 100、关联文档。"""
    from app.services.ai import client as ai_client
    from app.services.insights import report_jobs

    # 让后台任务使用测试内存库
    monkeypatch.setattr(report_jobs, "engine", engine)
    monkeypatch.setattr(ai_client, "is_available", lambda *a, **k: False)

    sid = _stock(session)
    session.add(Watchlist(stock_id=sid))
    _price(session, sid, date(2026, 5, 28), "100")
    _price(session, sid, date(2026, 5, 29), "110")
    session.commit()

    job, _ = report_jobs.create_job(session, "US")
    report_jobs.run_job(job.id)

    session.expire_all()
    done = session.get(ReportJob, job.id)
    assert done.status == JOB_SUCCESS
    assert done.progress == 100
    assert done.document_id is not None
    assert done.finished_at is not None
    # 关联到真实文档
    doc = session.get(InsightDocument, done.document_id)
    assert doc is not None
    assert doc.doc_type == "DAILY_REPORT"


def test_generate_endpoint_returns_job(client, session: Session, monkeypatch) -> None:
    """POST 生成接口立即返回任务，不阻塞；重复请求复用任务。"""
    from app.services.insights import report_jobs

    # 后台任务置空，避免触发真实生成
    monkeypatch.setattr(report_jobs, "run_job", lambda job_id: None)

    r1 = client.post("/api/v1/insights/daily/generate?market=US")
    assert r1.status_code == 200
    body1 = r1.json()
    assert body1["code"] == 0
    job_id = body1["data"]["id"]
    assert body1["data"]["status"] == JOB_PENDING
    assert body1["data"]["market"] == "US"

    # 任务状态可查询
    rs = client.get(f"/api/v1/insights/daily/jobs/{job_id}")
    assert rs.status_code == 200
    assert rs.json()["data"]["id"] == job_id

    # 重复请求复用（同一 job id）
    r2 = client.post("/api/v1/insights/daily/generate?market=US")
    assert r2.json()["data"]["id"] == job_id


def test_generate_endpoint_rejects_unknown_market(client) -> None:
    r = client.post("/api/v1/insights/daily/generate?market=XX")
    assert r.status_code == 422


def test_delete_document(client, session: Session) -> None:
    """删除文档：成功移除，并解除任务引用。"""
    doc = InsightDocument(doc_type="DAILY_REPORT", market="US", title="t", body_md="x")
    session.add(doc)
    session.commit()
    session.refresh(doc)
    doc_id = doc.id

    # 关联一个已完成任务，删除后引用应被置空
    job = ReportJob(market="US", status=JOB_SUCCESS, document_id=doc_id)
    session.add(job)
    session.commit()
    job_id = job.id

    r = client.delete(f"/api/v1/insights/documents/{doc_id}")
    assert r.status_code == 200
    assert r.json()["data"]["deleted"] == doc_id

    session.expire_all()
    assert session.get(InsightDocument, doc_id) is None
    assert session.get(ReportJob, job_id).document_id is None


def test_delete_missing_document(client) -> None:
    r = client.delete("/api/v1/insights/documents/99999")
    assert r.status_code == 404
