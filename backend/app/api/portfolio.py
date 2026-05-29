"""组合接口：持仓、汇总。"""

from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, Depends
from sqlmodel import Session

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
    currency: str = "JPY",  # noqa: ARG001  多币种换算 Phase 2 接入
    session: Session = Depends(get_session),
) -> dict:
    """组合汇总：总成本、总市值、总浮盈、总已实现盈亏、持仓数。

    注意：当前为原币种相加（多币种统一换算在 Phase 2 Step 2.2 接入），
    跨币种混合时该汇总仅在单一币种组合下精确。
    """
    items = pnl_service.compute_all_holdings(session)
    total_cost = ZERO
    total_mv = ZERO
    total_upnl = ZERO
    total_realized = ZERO
    mv_available = True

    for ph in items:
        h = ph.holding
        total_cost += h.cost_basis
        total_realized += h.realized_pnl
        mv = h.market_value(ph.last_price)
        if mv is None:
            mv_available = False
        else:
            total_mv += mv
            upnl = h.unrealized_pnl(ph.last_price)
            if upnl is not None:
                total_upnl += upnl

    return ok(
        {
            "positions": len(items),
            "total_cost": to_db_str(quantize_money(total_cost)),
            "total_market_value": to_db_str(quantize_money(total_mv)) if mv_available else None,
            "total_unrealized_pnl": to_db_str(quantize_money(total_upnl)) if mv_available else None,
            "total_realized_pnl": to_db_str(quantize_money(total_realized)),
            "market_value_available": mv_available,
        }
    )
