"""管理接口：行情同步触发与状态。"""

from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, Query
from sqlmodel import Session, select

from app.core.response import Meta, ok
from app.database import engine, get_session
from app.logging_config import get_logger
from app.models.sync_log import SyncLog
from app.services.data_sync.sync_service import sync_market_prices

router = APIRouter(prefix="/admin", tags=["admin"])
log = get_logger(__name__)


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


@router.post("/sync/financials", summary="同步财务/估值指标")
def sync_financials(
    market: str | None = Query(None, description="限定市场；空为全部已登记股票"),
    session: Session = Depends(get_session),
) -> dict:
    """拉取财务/估值指标并 UPSERT 到 financials。"""
    from sqlalchemy.dialects.sqlite import insert as sqlite_insert

    from app.models.financials import Financial
    from app.models.stock import Stock
    from app.services.data_sync.financials_client import fetch_financials
    from app.services.data_sync.yfinance_client import YFinanceUnavailable

    stmt = select(Stock)
    if market:
        stmt = stmt.where(Stock.market == market.upper())
    stocks = list(session.exec(stmt).all())

    updated = 0
    failed: list[str] = []
    for stock in stocks:
        try:
            data = fetch_financials(stock.symbol, stock.market)
        except YFinanceUnavailable as e:
            return ok({"ok": False, "message": str(e)})
        if not data:
            failed.append(stock.symbol)
            continue
        values = {"stock_id": stock.id, **data}
        ins = sqlite_insert(Financial).values(**values)
        ins = ins.on_conflict_do_update(
            index_elements=["stock_id", "as_of"],
            set_={k: ins.excluded[k] for k in data if k != "as_of"},
        )
        session.exec(ins)
        updated += 1
    session.commit()
    return ok({"updated": updated, "failed": failed, "total": len(stocks)})


def _seed_universe_task(market: str | None, do_sync: bool) -> None:
    """后台任务：扩充股票池。"""
    try:
        from scripts.seed_universe import seed_universe

        markets = [market.upper()] if market else ["US", "HK", "JP", "CN"]
        seed_universe(markets, do_sync=do_sync)
    except Exception as e:  # noqa: BLE001
        log.warning("admin.seed_universe_failed", market=market, error=str(e))


@router.post("/seed-universe", summary="扩充股票池（成分股）")
def seed_universe_endpoint(
    background_tasks: BackgroundTasks,
    market: str | None = Query(None, description="US/CN/HK/JP；空为全部"),
    sync: bool = Query(True, description="是否同步行情/财务"),
) -> dict:
    """后台批量登记各市场精选成分股并同步。"""
    background_tasks.add_task(_seed_universe_task, market, sync)
    return ok({"status": "seeding", "market": market or "ALL"})


@router.get("/universe-status", summary="股票池数据完备度")
def universe_status(session: Session = Depends(get_session)) -> dict:
    """各市场：已登记 / 有行情 / 有财务 计数。"""
    from app.models.financials import Financial
    from app.models.stock import Price, Stock

    out: dict[str, dict] = {}
    for market in ("US", "CN", "HK", "JP"):
        stocks = list(session.exec(select(Stock).where(Stock.market == market)).all())
        registered = len(stocks)
        with_price = 0
        with_fin = 0
        for st in stocks:
            if session.exec(select(Price.date).where(Price.stock_id == st.id).limit(1)).first():
                with_price += 1
            if session.exec(select(Financial.id).where(Financial.stock_id == st.id).limit(1)).first():
                with_fin += 1
        out[market] = {
            "registered": registered,
            "with_price": with_price,
            "with_financials": with_fin,
        }
    return ok(out)
