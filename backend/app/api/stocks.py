"""股票相关接口：搜索、登记、详情、行情查询。"""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlmodel import Session, select

from app.core.money import to_db_str
from app.core.response import Meta, ok
from app.database import get_session
from app.models.stock import Price, Stock

router = APIRouter(prefix="/stocks", tags=["stocks"])


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


@router.post("", summary="登记股票")
def create_stock(payload: StockCreate, session: Session = Depends(get_session)) -> dict:
    """登记一只股票（symbol+market 唯一，已存在则返回现有）。"""
    existing = session.exec(
        select(Stock).where(
            Stock.symbol == payload.symbol, Stock.market == payload.market.upper()
        )
    ).first()
    if existing:
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
    return ok(stock)


@router.get("/search", summary="搜索股票")
def search_stocks(
    q: str = Query("", description="代码或名称关键字"),
    market: str | None = Query(None),
    limit: int = Query(20, le=100),
    session: Session = Depends(get_session),
) -> dict:
    """按代码/名称模糊搜索。"""
    stmt = select(Stock)
    if market:
        stmt = stmt.where(Stock.market == market.upper())
    if q:
        like = f"%{q}%"
        stmt = stmt.where((Stock.symbol.like(like)) | (Stock.name.like(like)))  # type: ignore[attr-defined]
    stmt = stmt.limit(limit)
    rows = list(session.exec(stmt).all())
    return ok(rows, meta=Meta(total=len(rows)))


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
