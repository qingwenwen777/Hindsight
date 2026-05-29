"""基准对比 API。"""

from __future__ import annotations

from datetime import date, timedelta

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session, select

from app.core.response import ok
from app.database import get_session
from app.models.stock import Price, Stock
from app.services.analysis import pnl as pnl_service
from app.services.analysis.benchmark import (
    DEFAULT_BENCHMARKS,
    compare,
    returns_from_prices,
)

router = APIRouter(prefix="/portfolio", tags=["benchmark"])


def _price_map(session: Session, stock_id: int, start: date) -> dict[date, float]:
    rows = session.exec(
        select(Price.date, Price.close).where(
            Price.stock_id == stock_id, Price.date >= start
        ).order_by(Price.date)
    ).all()
    return {d: float(c) for d, c in rows}


def _portfolio_daily_values(session: Session, start: date) -> dict[date, float]:
    """用当前持仓股数 × 历史价构造组合每日估值序列（近似）。

    说明：缺少历史持仓快照时的近似口径，假设持仓结构不变，
    用于估计 β / 跟踪误差等相对指标。
    """
    holdings = pnl_service.compute_all_holdings(session)
    # 收集每只股票的价格表
    per_stock: list[tuple[float, dict[date, float]]] = []
    all_dates: set[date] = set()
    for ph in holdings:
        shares = float(ph.holding.shares)
        pmap = _price_map(session, ph.stock.id, start)  # type: ignore[arg-type]
        if pmap:
            per_stock.append((shares, pmap))
            all_dates.update(pmap.keys())
    if not per_stock:
        return {}

    values: dict[date, float] = {}
    for d in sorted(all_dates):
        total = 0.0
        for shares, pmap in per_stock:
            if d in pmap:
                total += shares * pmap[d]
        values[d] = total
    return values


@router.get("/benchmark-comparison", summary="基准对比")
def benchmark_comparison(
    benchmark_market: str = Query("US", description="用哪个市场的默认基准"),
    benchmark_stock_id: int | None = Query(None, description="自定义基准股票 id"),
    days: int = Query(180, description="回溯天数"),
    session: Session = Depends(get_session),
) -> dict:
    """组合 vs 基准：alpha / 信息比率 / 跟踪误差 / β。

    基准优先用 benchmark_stock_id；否则用 benchmark_market 的默认基准（需已登记并同步行情）。
    """
    start = date.today() - timedelta(days=days)

    # 解析基准股票
    bench_default = DEFAULT_BENCHMARKS.get(benchmark_market.upper())
    bench: Stock | None = None
    if benchmark_stock_id:
        bench = session.get(Stock, benchmark_stock_id)
    elif bench_default:
        bench = session.exec(
            select(Stock).where(Stock.symbol == bench_default["symbol"])
        ).first()

    if not bench:
        return ok(
            {
                "available": False,
                "message": "未找到基准行情，请先登记并同步基准（如 000300/^GSPC）",
                "default_benchmark": bench_default,
            }
        )

    bench_prices_map = _price_map(session, bench.id, start)  # type: ignore[arg-type]
    port_values_map = _portfolio_daily_values(session, start)

    # 对齐共同日期
    common = sorted(set(bench_prices_map) & set(port_values_map))
    if len(common) < 3:
        return ok(
            {
                "available": False,
                "message": "组合与基准的重叠交易日不足，无法计算（需更多行情数据）",
            }
        )

    port_series = [port_values_map[d] for d in common]
    bench_series = [bench_prices_map[d] for d in common]
    port_returns = returns_from_prices(port_series)
    bench_returns = returns_from_prices(bench_series)

    result = compare(port_returns, bench_returns)
    return ok(
        {
            "available": True,
            "benchmark": {"symbol": bench.symbol, "name": bench.name},
            "portfolio_return": result.portfolio_return,
            "benchmark_return": result.benchmark_return,
            "alpha": result.alpha,
            "beta": result.beta,
            "tracking_error": result.tracking_error,
            "information_ratio": result.information_ratio,
            "samples": result.n,
        }
    )
