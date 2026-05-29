"""基准对比 —— alpha / 信息比率 / 跟踪误差 / β（设计文档 5.4）。

核心是纯函数：给定组合日收益率序列与基准日收益率序列（等长、对齐），
计算各指标。数据获取（构造序列）由 API 层负责。
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

# 每市场默认基准（symbol, market）
DEFAULT_BENCHMARKS: dict[str, dict] = {
    "CN": {"symbol": "000300", "name": "沪深300"},
    "US": {"symbol": "^GSPC", "name": "S&P 500"},
    "HK": {"symbol": "^HSI", "name": "恒生指数"},
    "JP": {"symbol": "^N225", "name": "日经225"},
}

TRADING_DAYS = 252


@dataclass
class BenchmarkComparison:
    """基准对比结果（年化口径）。"""

    portfolio_return: float  # 期间累计收益
    benchmark_return: float
    alpha: float  # 年化 alpha（Jensen 近似：用回归截距年化）
    beta: float
    tracking_error: float  # 年化跟踪误差
    information_ratio: float
    n: int  # 样本数


def _to_array(returns: list[float]) -> np.ndarray:
    return np.asarray([float(x) for x in returns], dtype="float64")


def compare(
    portfolio_returns: list[float],
    benchmark_returns: list[float],
    risk_free_daily: float = 0.0,
) -> BenchmarkComparison:
    """计算基准对比指标。

    - beta：cov(p,b)/var(b)
    - alpha：CAPM 回归截距（日），年化 ×252
    - tracking_error：(p-b) 的标准差，年化 ×sqrt(252)
    - information_ratio：年化超额收益均值 / 年化跟踪误差
    """
    p = _to_array(portfolio_returns)
    b = _to_array(benchmark_returns)
    n = min(len(p), len(b))
    if n < 2:
        raise ValueError("样本不足（至少 2 个收益点）")
    p = p[-n:]
    b = b[-n:]

    # 累计收益
    port_cum = float(np.prod(1 + p) - 1)
    bench_cum = float(np.prod(1 + b) - 1)

    # beta
    var_b = float(np.var(b, ddof=1))
    cov_pb = float(np.cov(p, b, ddof=1)[0, 1])
    beta = cov_pb / var_b if var_b != 0 else 0.0

    # alpha（CAPM 日截距）：E[p-rf] = alpha + beta*E[b-rf]
    excess_p = p - risk_free_daily
    excess_b = b - risk_free_daily
    alpha_daily = float(np.mean(excess_p) - beta * np.mean(excess_b))
    alpha_annual = alpha_daily * TRADING_DAYS

    # tracking error & information ratio
    active = p - b
    te_daily = float(np.std(active, ddof=1))
    te_annual = te_daily * np.sqrt(TRADING_DAYS)
    active_mean_annual = float(np.mean(active)) * TRADING_DAYS
    ir = active_mean_annual / te_annual if te_annual != 0 else 0.0

    return BenchmarkComparison(
        portfolio_return=round(port_cum, 6),
        benchmark_return=round(bench_cum, 6),
        alpha=round(alpha_annual, 6),
        beta=round(beta, 6),
        tracking_error=round(te_annual, 6),
        information_ratio=round(ir, 6),
        n=n,
    )


def returns_from_prices(prices: list[float]) -> list[float]:
    """价格序列 → 日收益率序列（长度 -1）。"""
    arr = _to_array(prices)
    if len(arr) < 2:
        return []
    return list((arr[1:] - arr[:-1]) / arr[:-1])
