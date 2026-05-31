"""决策审计测试：信心校准 + 决策类别聚合。"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from sqlmodel import Session

from app.models.journal import Journal
from app.models.stock import Price, Stock
from app.models.transaction import Transaction
from app.services.biases.decision_audit import (
    category_aggregation,
    confidence_calibration,
)


def _stock(session: Session, symbol: str) -> Stock:
    s = Stock(symbol=symbol, market="CN", name=symbol, currency="CNY")
    session.add(s)
    session.commit()
    session.refresh(s)
    return s


def _buy_with_journal(
    session: Session,
    *,
    symbol: str,
    confidence: int | None,
    category: str | None,
    ret_30d_pct: float,
) -> None:
    """造一笔带日志的买入，并铺 30 天后价格以产生指定回报。"""
    s = _stock(session, symbol)
    j = Journal(
        stock_id=s.id,
        decision_type="BUY",
        thesis="t",
        confidence=confidence,
        thesis_category=category,
        is_locked=True,
    )
    session.add(j)
    session.commit()
    session.refresh(j)

    buy_d = date(2026, 1, 1)
    base = Decimal("100")
    session.add(
        Transaction(
            stock_id=s.id, type="BUY", trade_date=buy_d, quantity="100",
            price=str(base), currency="CNY", journal_id=j.id,
            commission="0", tax="0", other_fees="0",
        )
    )
    session.add(Price(stock_id=s.id, date=buy_d, close=str(base)))
    end_price = base * (Decimal("1") + Decimal(str(ret_30d_pct)) / Decimal("100"))
    session.add(Price(stock_id=s.id, date=buy_d + timedelta(days=30), close=str(end_price)))
    session.commit()


def test_confidence_calibration_detects_overconfidence(session: Session) -> None:
    """高信心(5)但多数亏损 → 实际胜率低于隐含，gap 为负，给过度自信结论。"""
    # 4 笔信心=5：1 赢 3 亏 → 实际胜率 25%，隐含 90%
    _buy_with_journal(session, symbol="A1", confidence=5, category="GROWTH", ret_30d_pct=10)
    _buy_with_journal(session, symbol="A2", confidence=5, category="GROWTH", ret_30d_pct=-8)
    _buy_with_journal(session, symbol="A3", confidence=5, category="GROWTH", ret_30d_pct=-12)
    _buy_with_journal(session, symbol="A4", confidence=5, category="GROWTH", ret_30d_pct=-5)

    rows, conclusions = confidence_calibration(session)
    row5 = next(r for r in rows if r.confidence == 5)
    assert row5.n == 4
    assert row5.actual_win_rate == 0.25
    assert row5.implied_win_rate == 0.90
    assert row5.gap < 0  # 过度自信
    assert any("过度自信" in c for c in conclusions)


def test_category_aggregation_ranks_categories(session: Session) -> None:
    """不同类别分别统计胜率/平均回报。"""
    # VALUATION：2 笔都赢
    _buy_with_journal(session, symbol="V1", confidence=3, category="VALUATION", ret_30d_pct=15)
    _buy_with_journal(session, symbol="V2", confidence=3, category="VALUATION", ret_30d_pct=5)
    # EVENT：2 笔都亏
    _buy_with_journal(session, symbol="E1", confidence=4, category="EVENT", ret_30d_pct=-10)
    _buy_with_journal(session, symbol="E2", confidence=4, category="EVENT", ret_30d_pct=-6)

    rows, _ = category_aggregation(session)
    by_key = {r.key: r for r in rows}
    assert by_key["VALUATION"].n == 2
    assert by_key["VALUATION"].win_rate == 1.0
    assert by_key["EVENT"].win_rate == 0.0
    assert by_key["VALUATION"].avg_return == Decimal("10")  # (15+5)/2
    assert by_key["EVENT"].avg_return == Decimal("-8")  # (-10-6)/2
