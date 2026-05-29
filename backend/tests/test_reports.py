"""报表测试：月度汇总 + 失败案例库。"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from sqlmodel import Session

from app.models.journal import Journal
from app.models.stock import Price, Stock
from app.models.transaction import Transaction
from app.services.analysis.reports import build_failure_library, build_period_report


def _stock(session, symbol="T"):  # noqa: ANN001
    s = Stock(symbol=symbol, market="CN", name=symbol, currency="CNY")
    session.add(s)
    session.commit()
    session.refresh(s)
    return s


def test_monthly_report(session: Session) -> None:
    """月度报表统计买卖笔数与金额。"""
    s = _stock(session)
    session.add(
        Transaction(
            stock_id=s.id, type="BUY", trade_date=date(2026, 3, 5),
            quantity="100", price="10", currency="CNY",
            commission="5", tax="0", other_fees="0",
        )
    )
    session.add(
        Transaction(
            stock_id=s.id, type="SELL", trade_date=date(2026, 3, 20),
            quantity="50", price="12", currency="CNY",
            commission="3", tax="0", other_fees="0",
        )
    )
    # 不在 3 月的交易不计入
    session.add(
        Transaction(
            stock_id=s.id, type="BUY", trade_date=date(2026, 4, 1),
            quantity="100", price="10", currency="CNY",
            commission="0", tax="0", other_fees="0",
        )
    )
    session.commit()

    r = build_period_report(session, 2026, month=3)
    assert r.buy_count == 1
    assert r.sell_count == 1
    assert r.total_buy_amount == Decimal("1000")
    assert r.total_sell_amount == Decimal("600")
    assert r.total_fees == Decimal("8")


def test_failure_library(session: Session) -> None:
    """买入后 30 天跌 > 5% 进入失败库。"""
    s = _stock(session)
    j = Journal(stock_id=s.id, decision_type="BUY", thesis="逻辑", emotion="FOMO", is_locked=True)
    session.add(j)
    session.commit()
    session.refresh(j)
    buy_d = date(2026, 1, 1)
    session.add(
        Transaction(
            stock_id=s.id, type="BUY", trade_date=buy_d, quantity="100", price="100",
            currency="CNY", journal_id=j.id, commission="0", tax="0", other_fees="0",
        )
    )
    session.add(Price(stock_id=s.id, date=buy_d, close="100"))
    session.add(Price(stock_id=s.id, date=buy_d + timedelta(days=30), close="80"))  # -20%
    session.commit()

    cases = build_failure_library(session)
    assert len(cases) == 1
    assert cases[0].symbol == "T"
    assert cases[0].emotion == "FOMO"
    assert cases[0].return_30d == Decimal("-20")
