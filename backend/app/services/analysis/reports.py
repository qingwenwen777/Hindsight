"""报表服务：月/季/年度交易汇总 + 失败案例库。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from sqlmodel import Session, select

from app.core.money import D
from app.models.journal import Journal
from app.models.stock import Stock
from app.models.transaction import Transaction
from app.services.ai.context_builder import calc_return_pct

ZERO = Decimal("0")


@dataclass
class PeriodReport:
    period: str
    start: date
    end: date
    currency: str = "JPY"
    buy_count: int = 0
    sell_count: int = 0
    total_buy_amount: Decimal = ZERO
    total_sell_amount: Decimal = ZERO
    total_fees: Decimal = ZERO
    symbols_traded: list[str] = field(default_factory=list)
    is_estimated: bool = False


def _period_bounds(year: int, month: int | None = None, quarter: int | None = None) -> tuple[date, date]:
    """计算月/季/年的起止日期。"""
    if month is not None:
        start = date(year, month, 1)
        end = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
    elif quarter is not None:
        start_month = (quarter - 1) * 3 + 1
        start = date(year, start_month, 1)
        end_month = start_month + 3
        end = date(year + 1, 1, 1) if end_month > 12 else date(year, end_month, 1)
    else:
        start = date(year, 1, 1)
        end = date(year + 1, 1, 1)
    return start, end


def build_period_report(
    session: Session,
    year: int,
    month: int | None = None,
    quarter: int | None = None,
    currency: str = "JPY",
) -> PeriodReport:
    """构建某期间的交易汇总报表（金额按交易日汇率换算到 currency）。"""
    from app.core.currency import FxRateUnavailable, get_fx_quote

    currency = currency.upper()
    start, end = _period_bounds(year, month, quarter)
    label = (
        f"{year}-{month:02d}" if month else f"{year}Q{quarter}" if quarter else str(year)
    )
    report = PeriodReport(period=label, start=start, end=end, currency=currency)

    txs = session.exec(
        select(Transaction).where(
            Transaction.trade_date >= start, Transaction.trade_date < end
        )
    ).all()

    def _conv(amount: Decimal, from_ccy: str, on: date) -> Decimal:
        """把金额按交易日汇率换算到目标币种；缺失则标记估算并原样并入。"""
        from_ccy = (from_ccy or currency).upper()
        if from_ccy == currency:
            return amount
        try:
            q = get_fx_quote(session, from_ccy, currency, on)
            if q.is_estimated:
                report.is_estimated = True
            return amount * q.rate
        except FxRateUnavailable:
            report.is_estimated = True
            return amount

    symbols: set[str] = set()
    for tx in txs:
        ccy = (tx.currency or currency).upper()
        amount = _conv(D(tx.quantity) * D(tx.price), ccy, tx.trade_date)
        fees_raw = (tx.commission or ZERO) + (tx.tax or ZERO) + (tx.other_fees or ZERO)
        report.total_fees += _conv(D(fees_raw), ccy, tx.trade_date)
        if tx.type == "BUY":
            report.buy_count += 1
            report.total_buy_amount += amount
        else:
            report.sell_count += 1
            report.total_sell_amount += amount
        stock = session.get(Stock, tx.stock_id)
        if stock:
            symbols.add(stock.symbol)
    report.symbols_traded = sorted(symbols)
    return report


@dataclass
class FailureCase:
    transaction_id: int
    symbol: str
    name: str
    trade_date: str
    return_30d: Decimal
    emotion: str | None
    thesis: str | None


def build_failure_library(
    session: Session, loss_threshold_pct: Decimal = Decimal("5")
) -> list[FailureCase]:
    """失败案例库：买入后 30 天亏损 > 阈值 的交易聚合。"""
    txs = session.exec(select(Transaction).where(Transaction.type == "BUY")).all()
    cases: list[FailureCase] = []
    for tx in txs:
        ret = calc_return_pct(session, tx.stock_id, tx.trade_date, 30)
        if ret is None or ret >= -loss_threshold_pct:
            continue
        stock = session.get(Stock, tx.stock_id)
        journal = session.get(Journal, tx.journal_id) if tx.journal_id else None
        cases.append(
            FailureCase(
                transaction_id=tx.id,  # type: ignore[arg-type]
                symbol=stock.symbol if stock else "?",
                name=stock.name if stock else "?",
                trade_date=tx.trade_date.isoformat(),
                return_30d=ret,
                emotion=journal.emotion if journal else None,
                thesis=journal.thesis if journal else None,
            )
        )
    cases.sort(key=lambda c: c.return_30d)  # 最差在前
    return cases
