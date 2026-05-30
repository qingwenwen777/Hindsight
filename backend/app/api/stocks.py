"""股票相关接口：搜索、发现、登记、详情、行情查询。"""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlmodel import Session, select

from app.core.money import to_db_str
from app.core.response import Meta, ok
from app.database import engine, get_session
from app.logging_config import get_logger
from app.models.stock import Price, Stock

router = APIRouter(prefix="/stocks", tags=["stocks"])
log = get_logger(__name__)


class StockCreate(BaseModel):
    """登记股票入参。"""

    symbol: str
    market: str
    name: str
    name_en: str | None = None
    industry: str | None = None
    sector: str | None = None
    currency: str
    is_etf: bool = False
    sync: bool = False  # True 时登记后在后台拉取一次历史行情


def _sync_one_stock(stock_id: int) -> None:
    """后台任务：同步单只股票的历史行情（独立 session）。"""
    from app.services.data_sync.sync_service import sync_stock_prices

    try:
        with Session(engine) as session:
            stock = session.get(Stock, stock_id)
            if stock is None:
                return
            sync_stock_prices(session, stock, full=True)
    except Exception as e:  # noqa: BLE001  后台任务失败不影响请求
        log.warning("stocks.bg_sync_failed", stock_id=stock_id, error=str(e))


@router.post("", summary="登记股票")
def create_stock(
    payload: StockCreate,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session),
) -> dict:
    """登记一只股票（symbol+market 唯一，已存在则返回现有）。

    payload.sync=True 时，登记后在后台拉取一次历史行情（不阻塞响应）。
    """
    existing = session.exec(
        select(Stock).where(
            Stock.symbol == payload.symbol, Stock.market == payload.market.upper()
        )
    ).first()
    if existing:
        # 已存在但无行情且要求同步 → 触发一次后台同步
        if payload.sync:
            has_price = session.exec(
                select(Price.date).where(Price.stock_id == existing.id).limit(1)
            ).first()
            if not has_price:
                background_tasks.add_task(_sync_one_stock, existing.id)
        return ok(existing)
    stock = Stock(
        symbol=payload.symbol,
        market=payload.market.upper(),
        name=payload.name,
        name_en=payload.name_en,
        industry=payload.industry,
        sector=payload.sector,
        currency=payload.currency.upper(),
        is_etf=payload.is_etf,
    )
    session.add(stock)
    session.commit()
    session.refresh(stock)
    if payload.sync:
        background_tasks.add_task(_sync_one_stock, stock.id)
    return ok(stock)


@router.get("/search", summary="搜索股票")
def search_stocks(
    q: str = Query("", description="代码或名称关键字"),
    market: str | None = Query(None),
    limit: int = Query(20, le=100),
    session: Session = Depends(get_session),
) -> dict:
    """按代码/名称模糊搜索（本地库）。"""
    stmt = select(Stock)
    if market:
        stmt = stmt.where(Stock.market == market.upper())
    if q:
        like = f"%{q}%"
        stmt = stmt.where(
            (Stock.symbol.like(like))
            | (Stock.name.like(like))
            | (Stock.name_en.like(like))  # type: ignore[union-attr]
        )  # type: ignore[attr-defined]
    stmt = stmt.limit(limit)
    rows = list(session.exec(stmt).all())
    return ok(rows, meta=Meta(total=len(rows)))


@router.get("/discover", summary="从数据源发现股票")
def discover_stocks(
    q: str = Query(..., min_length=2, description="代码或名称关键字"),
    market: str | None = Query(None, description="限定市场：US/HK/JP/CN"),
    limit: int = Query(8, le=20),
    session: Session = Depends(get_session),
) -> dict:
    """通过外部数据源（yfinance）发现可登记的股票候选。

    返回候选列表，并标记本地是否已登记（registered + stock_id）。
    前端可据此做"一键添加并同步"。
    """
    from app.services.data_sync.discovery import discover_symbols
    from app.services.data_sync.yfinance_client import YFinanceUnavailable

    try:
        candidates = discover_symbols(q, market=market, limit=limit)
    except YFinanceUnavailable as e:
        # 数据源不可用时返回空列表（前端按"无结果"处理），错误信息放在 meta
        log.warning("stocks.discover_unavailable", q=q, error=str(e))
        return ok([], meta=Meta(total=0))

    # 标注本地已登记状态
    for c in candidates:
        existing = session.exec(
            select(Stock).where(
                Stock.symbol == c["symbol"], Stock.market == c["market"]
            )
        ).first()
        c["registered"] = existing is not None
        c["stock_id"] = existing.id if existing else None

    return ok(candidates, meta=Meta(total=len(candidates)))


@router.get("/{stock_id}", summary="股票详情")
def get_stock(stock_id: int, session: Session = Depends(get_session)) -> dict:
    """按 id 获取股票。"""
    stock = session.get(Stock, stock_id)
    if not stock:
        raise HTTPException(status_code=404, detail="股票不存在")
    return ok(stock)


@router.get("/{stock_id}/prices", summary="日线行情")
def get_prices(
    stock_id: int,
    start: date | None = Query(None),
    end: date | None = Query(None),
    session: Session = Depends(get_session),
) -> dict:
    """获取某股票日线行情（金额转字符串，前端用 Decimal 字符串展示）。"""
    if not session.get(Stock, stock_id):
        raise HTTPException(status_code=404, detail="股票不存在")
    stmt = select(Price).where(Price.stock_id == stock_id)
    if start:
        stmt = stmt.where(Price.date >= start)
    if end:
        stmt = stmt.where(Price.date <= end)
    stmt = stmt.order_by(Price.date)
    rows = list(session.exec(stmt).all())
    data = [
        {
            "date": p.date.isoformat(),
            "open": to_db_str(p.open),
            "high": to_db_str(p.high),
            "low": to_db_str(p.low),
            "close": to_db_str(p.close),
            "volume": p.volume,
            "turnover": to_db_str(p.turnover),
        }
        for p in rows
    ]
    return ok(data, meta=Meta(total=len(data)))


@router.get("/{stock_id}/indicators", summary="技术指标")
def get_indicators(
    stock_id: int,
    type: str | None = Query(None, description="逗号分隔：MA,EMA,MACD,RSI,BOLL,KDJ"),
    start: date | None = Query(None),
    end: date | None = Query(None),
    session: Session = Depends(get_session),
) -> dict:
    """计算某股票的技术指标（基于已同步的日线）。"""
    from app.services.analysis.indicators import compute_indicators

    if not session.get(Stock, stock_id):
        raise HTTPException(status_code=404, detail="股票不存在")
    stmt = select(Price).where(Price.stock_id == stock_id)
    if start:
        stmt = stmt.where(Price.date >= start)
    if end:
        stmt = stmt.where(Price.date <= end)
    stmt = stmt.order_by(Price.date)
    rows = list(session.exec(stmt).all())
    if not rows:
        return ok({"dates": [], "indicators": {}})

    dates = [p.date.isoformat() for p in rows]
    close = [float(p.close) for p in rows]
    high = [float(p.high) if p.high is not None else float(p.close) for p in rows]
    low = [float(p.low) if p.low is not None else float(p.close) for p in rows]
    types = [t.strip() for t in type.split(",")] if type else None
    indicators = compute_indicators(close, high, low, types)
    return ok({"dates": dates, "indicators": indicators})


@router.get("/{stock_id}/financials", summary="财务/估值指标")
def get_financials(stock_id: int, session: Session = Depends(get_session)) -> dict:
    """返回某股票最新的财务/估值快照。"""
    from app.models.financials import Financial

    if not session.get(Stock, stock_id):
        raise HTTPException(status_code=404, detail="股票不存在")
    fin = session.exec(
        select(Financial)
        .where(Financial.stock_id == stock_id)
        .order_by(Financial.as_of.desc())
        .limit(1)
    ).first()
    if not fin:
        return ok(None)
    return ok(
        {
            "as_of": fin.as_of.isoformat(),
            "pe": to_db_str(fin.pe),
            "pb": to_db_str(fin.pb),
            "roe": to_db_str(fin.roe),
            "revenue_yoy": to_db_str(fin.revenue_yoy),
            "profit_yoy": to_db_str(fin.profit_yoy),
            "market_cap": to_db_str(fin.market_cap),
            "dividend_yield": to_db_str(fin.dividend_yield),
            "eps": to_db_str(fin.eps),
            "source": fin.source,
        }
    )
