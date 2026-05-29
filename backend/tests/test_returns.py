"""TWR / IRR 单元测试 —— 已知答案的现金流序列。"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from app.services.analysis.returns import (
    CashFlowPoint,
    Subperiod,
    twr,
    xirr,
)


def test_twr_two_periods_known() -> None:
    """两段已知收益率几何相乘。

    段1：期初 100，无流入，期末 110 → r1 = 10%
    段2：期初 110，无流入，期末 121 → r2 = 10%
    TWR = 1.1 * 1.1 - 1 = 0.21
    """
    sp1 = Subperiod(begin_value=Decimal("100"), net_flow=Decimal("0"), end_value=Decimal("110"))
    sp2 = Subperiod(begin_value=Decimal("110"), net_flow=Decimal("0"), end_value=Decimal("121"))
    result = twr([sp1, sp2])
    assert result == Decimal("0.21")


def test_twr_excludes_cash_flow_effect() -> None:
    """资金注入不应被计成收益。

    段：期初 100，期间净存入 100（期初注入），期末 200 → 收益率 0（只是钱进来了）
    r = (200 - 100 - 100) / (100 + 100) = 0
    """
    sp = Subperiod(begin_value=Decimal("100"), net_flow=Decimal("100"), end_value=Decimal("200"))
    assert sp.rate() == Decimal("0")
    assert twr([sp]) == Decimal("0")


def test_irr_simple_one_year_double() -> None:
    """一年翻倍：-100 投入，一年后 +200 回收 → IRR = 100%。"""
    flows = [
        CashFlowPoint(when=date(2025, 1, 1), amount=Decimal("-100")),
        CashFlowPoint(when=date(2026, 1, 1), amount=Decimal("200")),
    ]
    result = xirr(flows)
    assert result is not None
    # 365 天 → 接近 1.0（100%）
    assert abs(result - Decimal("1.0")) < Decimal("0.01")


def test_irr_zero_return() -> None:
    """投入与回收相等且同期 → IRR ≈ 0。"""
    flows = [
        CashFlowPoint(when=date(2025, 1, 1), amount=Decimal("-100")),
        CashFlowPoint(when=date(2026, 1, 1), amount=Decimal("100")),
    ]
    result = xirr(flows)
    assert result is not None
    assert abs(result) < Decimal("0.001")


def test_irr_multiple_flows() -> None:
    """多笔现金流，验证可求解且在合理范围。

    -1000 (期初) , -500 (半年后追加) , +1700 (一年后全部回收)
    总投入约 1500，回收 1700，年化应为正且 < 50%。
    """
    flows = [
        CashFlowPoint(when=date(2025, 1, 1), amount=Decimal("-1000")),
        CashFlowPoint(when=date(2025, 7, 1), amount=Decimal("-500")),
        CashFlowPoint(when=date(2026, 1, 1), amount=Decimal("1700")),
    ]
    result = xirr(flows)
    assert result is not None
    assert Decimal("0") < result < Decimal("0.5")


def test_irr_no_solution() -> None:
    """全负现金流无解返回 None。"""
    flows = [
        CashFlowPoint(when=date(2025, 1, 1), amount=Decimal("-100")),
        CashFlowPoint(when=date(2026, 1, 1), amount=Decimal("-50")),
    ]
    assert xirr(flows) is None
