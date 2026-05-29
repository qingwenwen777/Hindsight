"""基准对比测试 —— 验证 beta/alpha/IR 计算。"""

from __future__ import annotations

import numpy as np

from app.services.analysis.benchmark import compare, returns_from_prices


def test_identical_series_beta_one_alpha_zero() -> None:
    """组合与基准完全相同 → beta=1，alpha=0，跟踪误差=0，IR=0。"""
    rng = np.random.default_rng(42)
    bench = list(rng.normal(0.001, 0.01, 60))
    result = compare(bench, bench)
    assert abs(result.beta - 1.0) < 1e-9
    assert abs(result.alpha) < 1e-9
    assert abs(result.tracking_error) < 1e-9
    assert result.information_ratio == 0.0


def test_leveraged_2x_beta_two() -> None:
    """组合 = 2 倍基准收益 → beta≈2。"""
    rng = np.random.default_rng(1)
    bench = list(rng.normal(0.0, 0.01, 100))
    port = [2 * x for x in bench]
    result = compare(port, bench)
    assert abs(result.beta - 2.0) < 1e-6


def test_constant_alpha() -> None:
    """组合每日比基准多固定 0.001 → alpha 年化 ≈ 0.001*252，beta≈1。

    port = bench + 0.001（常数超额），与基准完全相关。
    """
    rng = np.random.default_rng(7)
    bench = list(rng.normal(0.0, 0.01, 250))
    port = [x + 0.001 for x in bench]
    result = compare(port, bench)
    assert abs(result.beta - 1.0) < 1e-6
    # alpha 年化 ≈ 0.001 * 252 = 0.252
    assert abs(result.alpha - 0.252) < 1e-3
    # 跟踪误差应非常小（仅常数差异）
    assert result.tracking_error < 1e-6


def test_returns_from_prices() -> None:
    """价格 [100,110,121] → 收益 [0.1, 0.1]。"""
    r = returns_from_prices([100, 110, 121])
    assert len(r) == 2
    assert abs(r[0] - 0.1) < 1e-9
    assert abs(r[1] - 0.1) < 1e-9
