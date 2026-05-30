"""组合净值曲线构造（供风险指标 / 基准对比 / 前端净值曲线共用）。

口径说明：缺少逐日持仓快照时，用"当前持仓股数 × 历史价"近似每日组合估值，
假设持仓结构在区间内不变。用于估计回撤、波动、夏普等相对结构指标。
"""

from __future__ import annotations

from datetime import date, timedelta

from sqlmodel import Session, select

from app.models.stock import Price
from app.services.analysis import pnl as pnl_service


def build_equity_curve(
    session: Session, days: int | None = None
) -> tuple[list[str], list[float]]:
    """返回 (日期列表, 组合每日估值列表)。

    days 为 None 时取全部可用历史。
    """
    holdings = pnl_service.compute_all_holdings(session)
    if not holdings:
        return [], []

    start: date | None = None
    if days is not None:
        start = date.today() - timedelta(days=days)

    per_stock: list[tuple[float, dict[date, float]]] = []
    all_dates: set[date] = set()
    for ph in holdings:
        shares = float(ph.holding.shares)
        if shares == 0:
            continue
        stmt = select(Price.date, Price.close).where(Price.stock_id == ph.stock.id)
        if start is not None:
            stmt = stmt.where(Price.date >= start)
        stmt = stmt.order_by(Price.date)
        pmap = {d: float(c) for d, c in session.exec(stmt).all()}
        if pmap:
            per_stock.append((shares, pmap))
            all_dates.update(pmap.keys())

    if not per_stock:
        return [], []

    dates = sorted(all_dates)
    # 用前向填充：某股票某日无价则用其最近一个已知价
    last_known: dict[int, float] = {}
    equity: list[float] = []
    for d in dates:
        total = 0.0
        for idx, (shares, pmap) in enumerate(per_stock):
            if d in pmap:
                last_known[idx] = pmap[d]
            price = last_known.get(idx)
            if price is not None:
                total += shares * price
        equity.append(total)

    return [d.isoformat() for d in dates], equity
