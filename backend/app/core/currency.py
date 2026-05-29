"""多币种换算 —— 查 fx_rates 表，缺失回退最近交易日并标记估算。

汇率约定：FxRate(base, quote, rate) 表示 1 base = rate quote。
查询时支持：
- 直接汇率 base->quote
- 反向汇率 quote->base（取倒数）
- 经 JPY 中转（base->JPY->quote）作为兜底
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlmodel import Session, select

from app.core.money import D, Money
from app.models.fx_rate import FxRate


class FxRateUnavailable(Exception):
    """缺少汇率且无法回退时抛出。"""


@dataclass
class FxQuote:
    """一次换算的汇率结果，带是否估算标记。"""

    rate: Decimal
    is_estimated: bool
    rate_date: date | None


def _lookup_direct(
    session: Session, base: str, quote: str, on_date: date
) -> tuple[Decimal, date] | None:
    """查 base->quote 在 on_date 当天或之前最近一天的汇率。"""
    stmt = (
        select(FxRate)
        .where(
            FxRate.base_currency == base,
            FxRate.quote_currency == quote,
            FxRate.date <= on_date,
        )
        .order_by(FxRate.date.desc())
        .limit(1)
    )
    row = session.exec(stmt).first()
    if row is not None:
        return D(row.rate), row.date
    return None


def get_fx_quote(
    session: Session,
    base: str,
    quote: str,
    on_date: date | None = None,
) -> FxQuote:
    """获取 base->quote 汇率（带回退与估算标记）。"""
    base = base.upper()
    quote = quote.upper()
    if base == quote:
        return FxQuote(rate=D("1"), is_estimated=False, rate_date=on_date)

    on_date = on_date or date.today()

    # 1. 直接汇率
    direct = _lookup_direct(session, base, quote, on_date)
    if direct:
        rate, rdate = direct
        return FxQuote(rate=rate, is_estimated=(rdate != on_date), rate_date=rdate)

    # 2. 反向汇率取倒数
    inverse = _lookup_direct(session, quote, base, on_date)
    if inverse:
        rate, rdate = inverse
        if rate != 0:
            return FxQuote(rate=D("1") / rate, is_estimated=True, rate_date=rdate)

    # 3. 经 JPY 中转
    if base != "JPY" and quote != "JPY":
        leg1 = _lookup_direct(session, base, "JPY", on_date) or _inverse_leg(
            session, "JPY", base, on_date
        )
        leg2 = _lookup_direct(session, "JPY", quote, on_date) or _inverse_leg(
            session, quote, "JPY", on_date
        )
        if leg1 and leg2:
            (r1, d1), (r2, d2) = leg1, leg2
            return FxQuote(rate=r1 * r2, is_estimated=True, rate_date=min(d1, d2))

    raise FxRateUnavailable(f"无可用汇率：{base}->{quote}（含回退/中转均失败）")


def _inverse_leg(
    session: Session, base: str, quote: str, on_date: date
) -> tuple[Decimal, date] | None:
    """中转用：取反向腿的倒数。"""
    res = _lookup_direct(session, base, quote, on_date)
    if res and res[0] != 0:
        return D("1") / res[0], res[1]
    return None


def get_fx_rate(
    session: Session, base: str, quote: str, on_date: date | None = None
) -> Decimal:
    """便捷函数：仅取汇率数值。"""
    return get_fx_quote(session, base, quote, on_date).rate


def convert(
    session: Session, money: Money, target_currency: str, on_date: date | None = None
) -> Money:
    """把 Money 换算到目标币种。"""
    target_currency = target_currency.upper()
    if money.currency == target_currency:
        return money
    rate = get_fx_rate(session, money.currency, target_currency, on_date)
    return Money(money.amount * rate, target_currency)
