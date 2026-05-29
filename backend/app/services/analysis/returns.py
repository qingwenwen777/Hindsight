"""收益率计算 —— TWR（时间加权）与 IRR（内部收益率）。

设计文档 5.4：
- TWR：按现金流事件切分时间段，每段独立算收益率，几何相乘，排除资金进出影响。
- IRR：解 NPV=0 的年化收益率，用 scipy.optimize.brentq。

输入为净现金流序列 + 各时点市值。金额用 Decimal，但数值求解（brentq）
需要 float，仅在求解器内部转换，对外仍返回高精度结果。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from app.core.money import D

ZERO = Decimal("0")


@dataclass
class Subperiod:
    """TWR 子区间。

    begin_value: 期初市值
    net_flow: 期初之后、期末之前的净存入（入金为正）
    end_value: 期末市值
    收益率 r = (end_value - begin_value - net_flow) / (begin_value + net_flow)
    （采用 net_flow 在期初注入的口径，与文档一致的简化处理。）
    """

    begin_value: Decimal
    net_flow: Decimal
    end_value: Decimal

    def rate(self) -> Decimal:
        denom = self.begin_value + self.net_flow
        if denom == ZERO:
            return ZERO
        return (self.end_value - self.begin_value - self.net_flow) / denom


def twr(subperiods: list[Subperiod]) -> Decimal:
    """时间加权收益率：∏(1 + r_i) - 1。"""
    product = Decimal("1")
    for sp in subperiods:
        product *= Decimal("1") + sp.rate()
    return product - Decimal("1")


@dataclass
class CashFlowPoint:
    """IRR 用现金流点：(日期, 金额)。

    约定：投入（买入/入金）为负，回收（卖出/出金/期末市值）为正。
    """

    when: date
    amount: Decimal


def _xnpv(rate: float, flows: list[CashFlowPoint], t0: date) -> float:
    """带日期的 NPV（按年贴现，ACT/365）。"""
    total = 0.0
    for f in flows:
        days = (f.when - t0).days
        years = days / 365.0
        total += float(f.amount) / ((1.0 + rate) ** years)
    return total


def xirr(
    flows: list[CashFlowPoint],
    *,
    low: float = -0.9999,
    high: float = 1000.0,
) -> Decimal | None:
    """求年化 IRR（解 xnpv=0），用 brentq。

    需要现金流既有正又有负，否则无解返回 None。
    """
    if len(flows) < 2:
        return None
    signs = {1 if f.amount > 0 else -1 if f.amount < 0 else 0 for f in flows}
    if 1 not in signs or -1 not in signs:
        return None

    from scipy.optimize import brentq

    flows_sorted = sorted(flows, key=lambda f: f.when)
    t0 = flows_sorted[0].when

    f_low = _xnpv(low, flows_sorted, t0)
    f_high = _xnpv(high, flows_sorted, t0)
    if f_low * f_high > 0:
        # 区间端点同号，brentq 无法保证求根
        return None

    try:
        root = brentq(lambda r: _xnpv(r, flows_sorted, t0), low, high, maxiter=200, xtol=1e-10)
    except (ValueError, RuntimeError):
        return None
    # 转回 Decimal（限制精度）
    return D(str(round(root, 10)))


def simple_irr(flows: list[CashFlowPoint]) -> Decimal | None:
    """便捷封装，等同 xirr。"""
    return xirr(flows)
