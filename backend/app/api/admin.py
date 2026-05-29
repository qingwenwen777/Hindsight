"""管理接口：行情同步触发与状态。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session, select

from app.core.response import Meta, ok
from app.database import get_session
from app.models.sync_log import SyncLog
from app.services.data_sync.sync_service import sync_market_prices

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/sync/prices")
def sync_prices(
    market: str = Query(..., description="市场代码：CN / US / HK / JP"),
    full: bool = Query(False, description="是否全量重拉"),
    session: Session = Depends(get_session),
) -> dict:
    """触发某市场行情同步。"""
    report = sync_market_prices(session, market, full=full)
    return ok(
        {
            "market": report.market,
            "stocks": len(report.results),
            "inserted": report.total_inserted,
            "updated": report.total_updated,
            "failed": [
                {"symbol": r.symbol, "message": r.message} for r in report.failed
            ],
            "results": [
                {
                    "symbol": r.symbol,
                    "ok": r.ok,
                    "inserted": r.inserted,
                    "updated": r.updated,
                    "skipped": r.skipped,
                    "message": r.message,
                }
                for r in report.results
            ],
        }
    )


@router.get("/sync/logs", summary="同步日志")
def sync_logs(
    limit: int = Query(50, le=500),
    market: str | None = Query(None),
    session: Session = Depends(get_session),
) -> dict:
    """查询最近的同步日志。"""
    stmt = select(SyncLog)
    if market:
        stmt = stmt.where(SyncLog.market == market.upper())
    stmt = stmt.order_by(SyncLog.created_at.desc()).limit(limit)
    rows = list(session.exec(stmt).all())
    data = [
        {
            "id": r.id,
            "market": r.market,
            "symbol": r.symbol,
            "source": r.source,
            "ok": r.ok,
            "inserted": r.inserted,
            "updated": r.updated,
            "skipped": r.skipped,
            "message": r.message,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]
    return ok(data, meta=Meta(total=len(data)))


@router.get("/sync/status", summary="同步状态汇总")
def sync_status(session: Session = Depends(get_session)) -> dict:
    """各市场最近一次同步状态。"""
    out: dict[str, dict] = {}
    for market in ("CN", "US", "HK", "JP"):
        last = session.exec(
            select(SyncLog)
            .where(SyncLog.market == market)
            .order_by(SyncLog.created_at.desc())
            .limit(1)
        ).first()
        out[market] = (
            {
                "ok": last.ok,
                "source": last.source,
                "message": last.message,
                "at": last.created_at.isoformat() if last.created_at else None,
            }
            if last
            else None
        )
    return ok(out)


@router.post("/sync/fx", summary="同步汇率")
def sync_fx(
    days: int = Query(30, description="拉取最近 N 天"),
    session: Session = Depends(get_session),
) -> dict:
    """通过 yfinance 拉取汇率并写入 fx_rates。"""
    from app.services.data_sync.fx_client import sync_fx_rates
    from app.services.data_sync.yfinance_client import YFinanceUnavailable

    try:
        summary = sync_fx_rates(session, days=days)
    except YFinanceUnavailable as e:
        return ok({"ok": False, "message": str(e)})
    return ok(summary)
