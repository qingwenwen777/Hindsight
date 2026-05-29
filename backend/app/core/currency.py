"""多币种换算（占位 —— Phase 2 Step 2.2 接入 fx_rates 同步）。

当前提供接口骨架：
- `convert(money, target, on_date)`：换算（暂仅支持同币种直通）。
- 汇率查询函数 `get_fx_rate` 在 Phase 2 接 fx_rates 表 + yfinance 同步。
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from app.core.money import D, Money


class FxRateUnavailable(Exception):
    """缺少汇率且无法回退时抛出。"""


def get_fx_rate(
    base: str,
    quote: str,
    on_date: date | None = None,  # noqa: ARG001
) -> Decimal:
    """获取 base→quote 汇率。

    Phase 2 实现：查 fx_rates 表，缺失回退最近交易日并标记 is_estimated。
    当前占位：同币种返回 1，其它抛 FxRateUnavailable。
    """
    base = base.upper()
    quote = quote.upper()
    if base == quote:
        return D("1")
    raise FxRateUnavailable(
        f"汇率 {base}->{quote} 暂未实现（Phase 2 接入），当前仅支持同币种。"
    )


def convert(money: Money, target_currency: str, on_date: date | None = None) -> Money:
    """把 Money 换算到目标币种。"""
    target_currency = target_currency.upper()
    if money.currency == target_currency:
        return money
    rate = get_fx_rate(money.currency, target_currency, on_date)
    return Money(money.amount * rate, target_currency)
