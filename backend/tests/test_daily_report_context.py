"""日报上下文改进测试：持仓快照 / 行情新鲜度 / 事件驱动跳过。"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from sqlmodel import Session

from app.models.journal import Journal
from app.models.stock import Price, Stock
from app.models.transaction import Transaction
from app.services.insights.context import build_report_context
from app.services.insights.daily_report import build_daily_report


def _stock(session: Session, symbol: str) -> Stock:
    s = Stock(symbol=symbol, market="US", name=symbol, currency="USD")
    session.add(s)
    session.commit()
    session.refresh(s)
    return s


def test_context_includes_holding_snapshot(session: Session) -> None:
    """持仓快照应带权重、浮盈%、持有天数、当初逻辑。"""
    s = _stock(session, "AAPL")
    buy_d = date.today() - timedelta(days=40)
    j = Journal(
        stock_id=s.id, decision_type="BUY", thesis="便宜的好公司",
        thesis_category="VALUATION", is_locked=True,
    )
    session.add(j)
    session.add(
        Transaction(
            stock_id=s.id, type="BUY", trade_date=buy_d, quantity="10", price="100",
            currency="USD", commission="0", tax="0", other_fees="0",
        )
    )
    # 两天行情：100 -> 110（+10%），最新日期为今天
    session.add(Price(stock_id=s.id, date=date.today() - timedelta(days=1), close="100"))
    session.add(Price(stock_id=s.id, date=date.today(), close="110"))
    session.commit()

    ctx = build_report_context(session, "US", Decimal("5"), date.today())
    assert len(ctx.holdings) == 1
    h = ctx.holdings[0]
    assert h.symbol == "AAPL"
    assert h.thesis_category == "VALUATION"
    assert h.thesis == "便宜的好公司"
    assert h.hold_days == 40
    assert h.weight_pct == Decimal("100")  # 唯一持仓
    # 浮盈%：成本 1000，市值 1100 → +10%
    assert h.unrealized_pnl_pct == Decimal("10")
    assert ctx.data_as_of == date.today()
    assert ctx.is_stale is False


def test_context_flags_stale_data(session: Session) -> None:
    """最新行情日期早于报告日 → is_stale=True。"""
    s = _stock(session, "MSFT")
    session.add(Price(stock_id=s.id, date=date.today() - timedelta(days=5), close="50"))
    session.add(Price(stock_id=s.id, date=date.today() - timedelta(days=4), close="55"))
    # 关注但不持仓也会纳入行情新鲜度判断
    from app.models.watchlist import Watchlist

    session.add(Watchlist(stock_id=s.id))
    session.commit()

    ctx = build_report_context(session, "US", Decimal("5"), date.today())
    assert ctx.data_as_of == date.today() - timedelta(days=4)
    assert ctx.is_stale is True


def test_scheduled_report_skips_when_no_events(session: Session) -> None:
    """事件驱动：无异动/触价/待办时，定时任务(skip_if_empty)不生成文档。"""
    s = _stock(session, "NVDA")
    # 平稳行情，无超阈值异动，无触价，无待办
    session.add(Price(stock_id=s.id, date=date.today() - timedelta(days=1), close="100"))
    session.add(Price(stock_id=s.id, date=date.today(), close="100.5"))  # +0.5% < 5%
    from app.models.watchlist import Watchlist

    session.add(Watchlist(stock_id=s.id))
    session.commit()

    doc = build_daily_report(session, "US", on_date=date.today(), skip_if_empty=True)
    assert doc is None  # 跳过

    # 手动生成（skip_if_empty=False）仍出一篇
    doc2 = build_daily_report(session, "US", on_date=date.today(), skip_if_empty=False)
    assert doc2 is not None
