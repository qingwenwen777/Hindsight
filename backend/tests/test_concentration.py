"""暴露与集中度测试：超阈值标记。"""

from __future__ import annotations

from datetime import date

from sqlmodel import Session

from app.models.stock import Price, Stock
from app.models.transaction import Transaction
from app.services.analysis import pnl as pnl_service
from app.services.biases.concentration import compute_concentration


def _add_holding(session: Session, symbol, industry, qty, price, currency="JPY", market="JP"):  # noqa: ANN001
    s = Stock(symbol=symbol, market=market, name=symbol, currency=currency, industry=industry)
    session.add(s)
    session.commit()
    session.refresh(s)
    session.add(
        Transaction(
            stock_id=s.id,
            type="BUY",
            trade_date=date(2026, 1, 1),
            quantity=str(qty),
            price=str(price),
            currency=currency,
            commission="0",
            tax="0",
            other_fees="0",
        )
    )
    session.add(Price(stock_id=s.id, date=date(2026, 1, 2), close=str(price)))
    session.commit()
    return s


def test_single_stock_over_threshold(session: Session) -> None:
    """一只股票占比 > 20% 应被标记告警。"""
    pnl_service.invalidate_holdings_cache()
    # A: 市值 900000；B: 市值 100000 → A 占 90% > 20%
    _add_holding(session, "AAA", "科技", 9000, 100)
    _add_holding(session, "BBB", "金融", 1000, 100)

    report = compute_concentration(session, "JPY")
    assert report.total_value > 0
    top = report.by_stock[0]
    assert top.key == "AAA"
    assert top.over_threshold is True
    assert any("单股集中度过高" in a for a in report.alerts)


def test_single_industry_over_threshold(session: Session) -> None:
    """同行业合计 > 40% 应被标记。"""
    pnl_service.invalidate_holdings_cache()
    # 两只科技股各 30% → 行业 60% > 40%
    _add_holding(session, "T1", "科技", 3000, 100)
    _add_holding(session, "T2", "科技", 3000, 100)
    _add_holding(session, "F1", "金融", 4000, 100)

    report = compute_concentration(session, "JPY")
    tech = next(s for s in report.by_industry if s.key == "科技")
    assert tech.over_threshold is True
    assert any("单行业集中度过高" in a for a in report.alerts)


def test_no_alerts_when_balanced(session: Session) -> None:
    """均衡组合无告警。"""
    pnl_service.invalidate_holdings_cache()
    # 6 只各约 16.7%，不同行业
    for i in range(6):
        _add_holding(session, f"S{i}", f"行业{i}", 1000, 100)
    report = compute_concentration(session, "JPY")
    assert report.alerts == []
