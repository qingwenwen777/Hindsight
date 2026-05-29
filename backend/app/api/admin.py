"""管理接口：行情同步触发与状态。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session

from app.core.response import ok
from app.database import get_session
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
