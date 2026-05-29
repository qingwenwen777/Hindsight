"""组合接口：持仓、汇总。"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session

from app.core.currency import FxRateUnavailable, get_fx_quote
from app.core.money import quantize_money, to_db_str
from app.core.response import Meta, ok
from app.database import get_session
from app.services.analysis import pnl as pnl_service

router = APIRouter(prefix="/portfolio", tags=["portfolio"])

ZERO = Decimal("0")


@router.get("/holdings", summary="持仓列表")
def get_holdings(session: Session = Depends(get_session)) -> dict:
    """返回当前所有持仓（含 FIFO 成本、市值、浮盈、参考均价）。"""
    items = pnl_service.compute_all_holdings(session)
    data = []
    for ph in items:
        h = ph.holding
        mv = h.market_value(ph.last_price)
        upnl = h.unrealized_pnl(ph.last_price)
        data.append(
            {
                "stock_id": ph.stock.id,
                "symbol": ph.stock.symbol,
                "market": ph.stock.market,
                "name": ph.stock.name,
                "currency": ph.stock.currency,
                "shares": to_db_str(h.shares),
                "avg_cost": to_db_str(quantize_money(h.avg_cost, Decimal("0.0001"))),
                "cost_basis": to_db_str(quantize_money(h.cost_basis)),
                "last_price": to_db_str(ph.last_price),
                "market_value": to_db_str(quantize_money(mv)) if mv is not None else None,
                "unrealized_pnl": to_db_str(quantize_money(upnl)) if upnl is not None else None,
                "realized_pnl": to_db_str(quantize_money(h.realized_pnl)),
            }
        )
    return ok(data, meta=Meta(total=len(data)))


@router.get("/summary", summary="组合汇总")
def get_summary(
    currency: str = Query("JPY", description="基准币种 JPY/USD/CNY"),
    session: Session = Depends(get_session),
) -> dict:
    """组合汇总：按基准币种换算后汇总总成本、总市值、总浮盈、总已实现盈亏。

    跨币种通过 fx_rates 换算（缺失回退最近交易日并标记估算）。
    若某币种汇率完全缺失，则在 warnings 中标注，相关金额按原币种并入（可能不准）。
    """
    currency = currency.upper()
    items = pnl_service.compute_all_holdings(session)
    total_cost = ZERO
    total_mv = ZERO
    total_upnl = ZERO
    total_realized = ZERO
    mv_available = True
    estimated = False
    warnings: list[str] = []

    today = date.today()

    def _conv(amount: Decimal | None, from_ccy: str) -> Decimal | None:
        nonlocal estimated
        if amount is None:
            return None
        if from_ccy == currency:
            return amount
        try:
            q = get_fx_quote(session, from_ccy, currency, today)
            if q.is_estimated:
                estimated = True
            return amount * q.rate
        except FxRateUnavailable:
            warnings.append(f"缺少 {from_ccy}->{currency} 汇率，{from_ccy} 部分未换算")
            return amount  # 兜底：原币种并入

    for ph in items:
        h = ph.holding
        ccy = ph.stock.currency
        c = _conv(h.cost_basis, ccy)
        if c is not None:
            total_cost += c
        r = _conv(h.realized_pnl, ccy)
        if r is not None:
            total_realized += r
        mv = h.market_value(ph.last_price)
        if mv is None:
            mv_available = False
        else:
            cmv = _conv(mv, ccy)
            if cmv is not None:
                total_mv += cmv
            upnl = h.unrealized_pnl(ph.last_price)
            cupnl = _conv(upnl, ccy)
            if cupnl is not None:
                total_upnl += cupnl

    return ok(
        {
            "currency": currency,
            "positions": len(items),
            "total_cost": to_db_str(quantize_money(total_cost)),
            "total_market_value": to_db_str(quantize_money(total_mv)) if mv_available else None,
            "total_unrealized_pnl": to_db_str(quantize_money(total_upnl)) if mv_available else None,
            "total_realized_pnl": to_db_str(quantize_money(total_realized)),
            "market_value_available": mv_available,
            "is_estimated": estimated,
            "warnings": warnings,
        }
    )
