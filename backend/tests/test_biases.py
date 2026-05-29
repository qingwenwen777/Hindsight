"""认知偏差防御规则测试：持有时间、复仇交易、情绪审计。"""

from __future__ import annotations

from datetime import date, timedelta

from sqlmodel import Session

from app.models.journal import Journal
from app.models.stock import Price, Stock
from app.models.transaction import Transaction
from app.services.biases.cooling_period import detect_revenge_trade
from app.services.biases.emotion_audit import audit_emotions
from app.services.biases.holding_time import check_early_sell


def _stock(session: Session, symbol="T") -> Stock:
    s = Stock(symbol=symbol, market="CN", name=symbol, currency="CNY")
    session.add(s)
    session.commit()
    session.refresh(s)
    return s


def _buy_with_journal(session, sid, d, price, horizon="LONG", emotion="CALM"):  # noqa: ANN001
    j = Journal(
        stock_id=sid, decision_type="BUY", thesis="t", expected_horizon=horizon,
        emotion=emotion, is_locked=True,
    )
    session.add(j)
    session.commit()
    session.refresh(j)
    session.add(
        Transaction(
            stock_id=sid, type="BUY", trade_date=d, quantity="100", price=str(price),
            currency="CNY", journal_id=j.id, commission="0", tax="0", other_fees="0",
        )
    )
    session.commit()


def _price(session, sid, d, close):  # noqa: ANN001
    session.add(Price(stock_id=sid, date=d, close=str(close)))
    session.commit()


# ---- 持有时间警告 ----


def test_early_sell_long_triggers(session: Session) -> None:
    """声明 LONG，10 天就卖 → 警告。"""
    s = _stock(session)
    _buy_with_journal(session, s.id, date(2026, 1, 1), 100, horizon="LONG")
    w = check_early_sell(session, s.id, date(2026, 1, 11))
    assert w.triggered is True
    assert w.held_days == 10


def test_sell_after_long_hold_no_warning(session: Session) -> None:
    """声明 LONG，持有 100 天卖 → 不警告。"""
    s = _stock(session)
    _buy_with_journal(session, s.id, date(2026, 1, 1), 100, horizon="LONG")
    w = check_early_sell(session, s.id, date(2026, 4, 15))
    assert w.triggered is False


def test_short_horizon_no_warning(session: Session) -> None:
    """声明 SHORT，早卖不警告。"""
    s = _stock(session)
    _buy_with_journal(session, s.id, date(2026, 1, 1), 100, horizon="SHORT")
    w = check_early_sell(session, s.id, date(2026, 1, 5))
    assert w.triggered is False


# ---- 复仇交易 ----


def test_revenge_trade_triggers(session: Session) -> None:
    """连续 3 次买入后 30 天均亏 → 复仇交易。"""
    s = _stock(session)
    # 3 笔买入，每笔后 30 天价格下跌
    for i, buy_d in enumerate([date(2026, 1, 1), date(2026, 2, 1), date(2026, 3, 1)]):
        _buy_with_journal(session, s.id, buy_d, 100)
        _price(session, s.id, buy_d, 100)
        _price(session, s.id, buy_d + timedelta(days=30), 80)  # 跌 20%

    decision = detect_revenge_trade(session, s.id)
    assert decision.is_revenge is True
    assert decision.seconds == 300
    assert decision.require_ai_confirm is True


def test_no_revenge_when_profitable(session: Session) -> None:
    """买入后盈利 → 非复仇交易。"""
    s = _stock(session)
    for buy_d in [date(2026, 1, 1), date(2026, 2, 1), date(2026, 3, 1)]:
        _buy_with_journal(session, s.id, buy_d, 100)
        _price(session, s.id, buy_d, 100)
        _price(session, s.id, buy_d + timedelta(days=30), 120)  # 涨

    decision = detect_revenge_trade(session, s.id)
    assert decision.is_revenge is False
    assert decision.seconds == 30


# ---- 情绪审计 ----


def test_emotion_audit_win_rate(session: Session) -> None:
    """FOMO 下亏、CALM 下盈，胜率应区分。"""
    s = _stock(session)
    # CALM 买入后涨
    _buy_with_journal(session, s.id, date(2026, 1, 1), 100, emotion="CALM")
    _price(session, s.id, date(2026, 1, 1), 100)
    _price(session, s.id, date(2026, 1, 31), 120)
    # FOMO 买入后跌
    _buy_with_journal(session, s.id, date(2026, 2, 1), 100, emotion="FOMO")
    _price(session, s.id, date(2026, 2, 1), 100)
    _price(session, s.id, date(2026, 3, 3), 80)

    stats = {st.emotion: st for st in audit_emotions(session)}
    assert stats["CALM"].win_rate == 1.0
    assert stats["FOMO"].win_rate == 0.0
