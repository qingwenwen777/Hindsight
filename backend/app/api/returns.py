"""组合收益率 API —— TWR / IRR。"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session, select

from app.core.money import D, to_db_str
from app.core.response import ok
from app.database import get_session
from app.models.cash import CashFlow
from app.services.analysis import pnl as pnl_service
from app.services.analysis.returns import CashFlowPoint, xirr

router = APIRouter(prefix="/portfolio", tags=["returns"])

ZERO = Decimal("0")

# 外部资金进出类型（用于 IRR：入金为投入=负，出金为回收=正）
_EXTERNAL_TYPES = {"DEPOSIT", "WITHDRAW"}


def _current_portfolio_value(session: Session) -> Decimal:
    """当前组合市值（无最新价的持仓按成本计）。"""
    items = pnl_service.compute_all_holdings(session)
    total = ZERO
    for ph in items:
        mv = ph.holding.market_value(ph.last_price)
        total += mv if mv is not None else ph.holding.cost_basis
    return total


@router.get("/returns", summary="组合收益率 (TWR/IRR)")
def get_returns(
    type: str = Query("IRR", description="TWR 或 IRR"),
    session: Session = Depends(get_session),
) -> dict:
    """计算组合收益率。

    IRR：用外部资金进出（DEPOSIT 入金=负 / WITHDRAW 出金=正）+ 当前市值（正）求解。
    TWR：当前实现基于现金流切段的简化口径（需要逐日估值序列才能精确，
         在缺少历史估值快照时退化为按外部现金流分段，返回近似值）。
    """
    rtype = type.upper()
    flows = list(session.exec(select(CashFlow).order_by(CashFlow.flow_date)).all())
    current_value = _current_portfolio_value(session)

    if rtype == "IRR":
        points: list[CashFlowPoint] = []
        for f in flows:
            if f.type.upper() in _EXTERNAL_TYPES:
                # 入金（amount>0）是投入 → IRR 现金流为负；出金（amount<0）是回收 → 为正
                points.append(CashFlowPoint(when=f.flow_date, amount=-D(f.amount)))
        # 期末市值作为正现金流
        if current_value != ZERO:
            points.append(CashFlowPoint(when=date.today(), amount=current_value))
        result = xirr(points)
        return ok(
            {
                "type": "IRR",
                "irr": to_db_str(result) if result is not None else None,
                "annualized_pct": to_db_str(result * 100) if result is not None else None,
                "current_value": to_db_str(current_value),
                "note": result is None and "现金流不足或无法求解" or None,
            }
        )

    # TWR（简化）：仅基于外部现金流分段，期末用当前市值
    from app.services.analysis.returns import Subperiod, twr

    deposits = [f for f in flows if f.type.upper() in _EXTERNAL_TYPES]
    total_deposit = sum((D(f.amount) for f in deposits), ZERO)
    if total_deposit == ZERO:
        return ok({"type": "TWR", "twr": None, "note": "无外部资金流，无法计算"})
    # 单段近似：begin=0, net_flow=总净存入, end=当前市值
    sp = Subperiod(begin_value=ZERO, net_flow=total_deposit, end_value=current_value)
    result = twr([sp])
    return ok(
        {
            "type": "TWR",
            "twr": to_db_str(result),
            "twr_pct": to_db_str(result * 100),
            "current_value": to_db_str(current_value),
            "note": "简化口径（单段）；逐日估值快照接入后将精确分段",
        }
    )
