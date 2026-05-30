"""风险指标测试 —— 已知答案样例。"""

from __future__ import annotations

from app.services.analysis.risk import (
    annualized_volatility,
    calmar_ratio,
    compute_risk_metrics,
    max_drawdown,
    returns_from_equity,
    sharpe_ratio,
)


def test_max_drawdown_known() -> None:
    """净值 100→120→90→110：峰值 120，谷底 90 → 回撤 (90-120)/120 = -25%。"""
    equity = [100, 120, 90, 110]
    mdd, underwater = max_drawdown(equity)
    assert mdd == -25.0
    assert len(underwater) == 4
    # 峰值点回撤为 0
    assert underwater[1].drawdown_pct == 0.0
    # 谷底回撤 -25
    assert underwater[2].drawdown_pct == -25.0


def test_no_drawdown_when_monotonic() -> None:
    """单调上涨无回撤。"""
    mdd, _ = max_drawdown([100, 101, 102, 103])
    assert mdd == 0.0


def test_returns_from_equity() -> None:
    r = returns_from_equity([100, 110, 121])
    assert abs(r[0] - 0.1) < 1e-9
    assert abs(r[1] - 0.1) < 1e-9


def test_sharpe_zero_vol() -> None:
    """恒定收益率 → 标准差 0 → 夏普 0（避免除零）。"""
    assert sharpe_ratio([0.01, 0.01, 0.01]) == 0.0


def test_sharpe_positive() -> None:
    """正收益且有波动 → 夏普为正。"""
    returns = [0.01, -0.005, 0.012, 0.008, -0.003, 0.015]
    assert sharpe_ratio(returns) > 0


def test_calmar() -> None:
    """卡玛 = 年化收益 / |最大回撤|。"""
    assert calmar_ratio(20.0, -10.0) == 2.0
    assert calmar_ratio(20.0, 0.0) == 0.0


def test_annualized_volatility_positive() -> None:
    vol = annualized_volatility([0.01, -0.01, 0.02, -0.015, 0.005])
    assert vol > 0


def test_compute_risk_metrics_integration() -> None:
    """综合：一段净值曲线计算所有指标且自洽。"""
    equity = [100, 105, 102, 110, 108, 115, 112, 120]
    metrics, underwater = compute_risk_metrics(equity)
    assert metrics.n == 8
    # 总收益 = 120/100 - 1 = 20%
    assert abs(metrics.total_return_pct - 20.0) < 1e-6
    # 最大回撤为负
    assert metrics.max_drawdown_pct < 0
    assert len(underwater) == 8
    assert metrics.annualized_volatility_pct > 0
