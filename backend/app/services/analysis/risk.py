"""风险指标 —— 最大回撤、夏普、卡玛、年化波动率（设计文档 F5.2）。

输入为净值序列（equity curve）或日收益率序列。
这些是统计量（非金额），用 float 计算即可，不要求 Decimal 精度。
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

TRADING_DAYS = 252


@dataclass
class DrawdownPoint:
    """回撤水下图的一个点。"""

    index: int
    drawdown_pct: float  # 负数或 0


@dataclass
class RiskMetrics:
    """风险指标汇总（年化口径）。"""

    total_return_pct: float
    annualized_return_pct: float
    annualized_volatility_pct: float
    max_drawdown_pct: float  # 负数
    sharpe: float
    calmar: float
    n: int


def _to_array(values: list[float]) -> np.ndarray:
    return np.asarray([float(v) for v in values], dtype="float64")


def returns_from_equity(equity: list[float]) -> list[float]:
    """净值序列 → 日收益率序列。"""
    arr = _to_array(equity)
    if len(arr) < 2:
        return []
    prev = arr[:-1]
    # 防止除零
    safe_prev = np.where(prev == 0, np.nan, prev)
    r = (arr[1:] - prev) / safe_prev
    return [0.0 if np.isnan(x) else float(x) for x in r]


def max_drawdown(equity: list[float]) -> tuple[float, list[DrawdownPoint]]:
    """最大回撤（%）+ 回撤水下序列。

    回撤 = (当前净值 - 历史峰值) / 历史峰值。最大回撤为最负值。
    """
    arr = _to_array(equity)
    if len(arr) == 0:
        return 0.0, []
    peak = arr[0]
    underwater: list[DrawdownPoint] = []
    mdd = 0.0
    for i, v in enumerate(arr):
        if v > peak:
            peak = v
        dd = (v - peak) / peak * 100 if peak != 0 else 0.0
        underwater.append(DrawdownPoint(index=i, drawdown_pct=round(dd, 4)))
        if dd < mdd:
            mdd = dd
    return round(mdd, 4), underwater


def sharpe_ratio(returns: list[float], risk_free_daily: float = 0.0) -> float:
    """年化夏普比率 = (日超额收益均值 / 日收益标准差) * sqrt(252)。"""
    r = _to_array(returns)
    if len(r) < 2:
        return 0.0
    excess = r - risk_free_daily
    std = float(np.std(excess, ddof=1))
    if std == 0:
        return 0.0
    return round(float(np.mean(excess)) / std * np.sqrt(TRADING_DAYS), 4)


def annualized_return(returns: list[float]) -> float:
    """几何年化收益率（%）。"""
    r = _to_array(returns)
    if len(r) == 0:
        return 0.0
    cumulative = float(np.prod(1 + r))
    if cumulative <= 0:
        return -100.0
    years = len(r) / TRADING_DAYS
    if years <= 0:
        return 0.0
    return round((cumulative ** (1 / years) - 1) * 100, 4)


def annualized_volatility(returns: list[float]) -> float:
    """年化波动率（%）。"""
    r = _to_array(returns)
    if len(r) < 2:
        return 0.0
    return round(float(np.std(r, ddof=1)) * np.sqrt(TRADING_DAYS) * 100, 4)


def calmar_ratio(annualized_return_pct: float, max_drawdown_pct: float) -> float:
    """卡玛比率 = 年化收益 / |最大回撤|。"""
    if max_drawdown_pct == 0:
        return 0.0
    return round(annualized_return_pct / abs(max_drawdown_pct), 4)


def compute_risk_metrics(
    equity: list[float], risk_free_daily: float = 0.0
) -> tuple[RiskMetrics, list[DrawdownPoint]]:
    """从净值序列计算全部风险指标。"""
    arr = _to_array(equity)
    returns = returns_from_equity(equity)
    total = (float(arr[-1]) / float(arr[0]) - 1) * 100 if len(arr) >= 2 and arr[0] != 0 else 0.0
    ann_ret = annualized_return(returns)
    ann_vol = annualized_volatility(returns)
    mdd, underwater = max_drawdown(equity)
    sharpe = sharpe_ratio(returns, risk_free_daily)
    calmar = calmar_ratio(ann_ret, mdd)
    metrics = RiskMetrics(
        total_return_pct=round(total, 4),
        annualized_return_pct=ann_ret,
        annualized_volatility_pct=ann_vol,
        max_drawdown_pct=mdd,
        sharpe=sharpe,
        calmar=calmar,
        n=len(arr),
    )
    return metrics, underwater
