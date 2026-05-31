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


def _current_portfolio_value(session: Session, currency: str | None = None) -> Decimal:
    """当前组合市值（无最新价的持仓按成本计）。

    currency 不为空时按当天汇率换算到基准币种，避免跨币种直接相加。
    """
    from datetime import date as _date

    from app.core.currency import FxRateUnavailable, get_fx_quote

    target = currency.upper() if currency else None
    items = pnl_service.compute_all_holdings(session)
    total = ZERO
    for ph in items:
        mv = ph.holding.market_value(ph.last_price)
        base_val = mv if mv is not None else ph.holding.cost_basis
        if target and ph.stock.currency and ph.stock.currency.upper() != target:
            try:
                q = get_fx_quote(session, ph.stock.currency, target, _date.today())
                base_val = base_val * q.rate
            except FxRateUnavailable:
                continue  # 缺汇率：跳过，不把未换算外币并入
        total += base_val
    return total


@router.get("/returns", summary="组合收益率 (TWR/IRR)")
def get_returns(
    type: str = Query("IRR", description="TWR 或 IRR"),
    currency: str = Query("JPY", description="基准币种 JPY/USD/CNY/HKD"),
    session: Session = Depends(get_session),
) -> dict:
    """计算组合收益率。

    IRR：用外部资金进出（DEPOSIT 入金=负 / WITHDRAW 出金=正）+ 当前市值（正）求解。
    TWR：当前实现基于现金流切段的简化口径（需要逐日估值序列才能精确，
         在缺少历史估值快照时退化为按外部现金流分段，返回近似值）。
    """
    currency = currency.upper()
    rtype = type.upper()
    flows = list(session.exec(select(CashFlow).order_by(CashFlow.flow_date)).all())
    current_value = _current_portfolio_value(session, currency)

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


@router.get("/risk-metrics", summary="风险指标 (回撤/夏普/卡玛)")
def get_risk_metrics(
    days: int | None = Query(None, description="回溯天数；空为全部"),
    currency: str = Query("JPY", description="基准币种 JPY/USD/CNY/HKD"),
    session: Session = Depends(get_session),
) -> dict:
    """基于组合净值曲线计算最大回撤、夏普、卡玛、年化波动等。"""
    from app.services.analysis.equity import build_equity_curve
    from app.services.analysis.risk import compute_risk_metrics

    dates, equity = build_equity_curve(session, days, currency.upper())
    if len(equity) < 2:
        return ok(
            {
                "available": False,
                "message": "净值数据不足（需要持仓 + 至少 2 个交易日行情）",
            }
        )
    metrics, underwater = compute_risk_metrics(equity)
    return ok(
        {
            "available": True,
            "total_return_pct": metrics.total_return_pct,
            "annualized_return_pct": metrics.annualized_return_pct,
            "annualized_volatility_pct": metrics.annualized_volatility_pct,
            "max_drawdown_pct": metrics.max_drawdown_pct,
            "sharpe": metrics.sharpe,
            "calmar": metrics.calmar,
            "samples": metrics.n,
            "drawdown_series": [
                {"date": dates[p.index], "drawdown_pct": p.drawdown_pct} for p in underwater
            ],
        }
    )


@router.get("/equity-curve", summary="组合净值曲线")
def get_equity_curve(
    days: int | None = Query(None, description="回溯天数；空为全部"),
    currency: str = Query("JPY", description="基准币种 JPY/USD/CNY/HKD"),
    session: Session = Depends(get_session),
) -> dict:
    """返回组合每日净值（归一化到起点 100）+ 原始市值。"""
    from app.services.analysis.equity import build_equity_curve

    dates, equity = build_equity_curve(session, days, currency.upper())
    if not equity:
        return ok({"dates": [], "equity": [], "normalized": []})
    base = equity[0] if equity[0] != 0 else 1.0
    normalized = [round(v / base * 100, 4) for v in equity]
    return ok(
        {
            "dates": dates,
            "equity": [round(v, 2) for v in equity],
            "normalized": normalized,
        }
    )
