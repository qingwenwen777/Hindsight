"""FIFO 持仓与盈亏单元测试 —— 含手算可验证样例。"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlmodel import Session

from app.models.corporate_action import CorporateAction
from app.models.stock import Stock
from app.models.transaction import Transaction
from app.services.analysis import pnl as pnl_service


def _stock(session: Session, symbol="TEST", market="CN", currency="CNY") -> Stock:
    s = Stock(symbol=symbol, market=market, name="测试", currency=currency)
    session.add(s)
    session.commit()
    session.refresh(s)
    return s


def _buy(session, sid, d, qty, price, fee="0"):  # noqa: ANN001
    session.add(
        Transaction(
            stock_id=sid,
            type="BUY",
            trade_date=d,
            quantity=Decimal(qty),
            price=Decimal(price),
            currency="CNY",
            commission=Decimal(fee),
        )
    )


def _sell(session, sid, d, qty, price, fee="0"):  # noqa: ANN001
    session.add(
        Transaction(
            stock_id=sid,
            type="SELL",
            trade_date=d,
            quantity=Decimal(qty),
            price=Decimal(price),
            currency="CNY",
            commission=Decimal(fee),
        )
    )


def test_fifo_buy_buy_sell(session: Session) -> None:
    """文档钦定样例：买100→买100→卖150（无费用，便于手算）。

    买1: 100股 @10 → lot[100,10]
    买2: 100股 @12 → lot[100,12]
    卖 : 150股 @15 → 收入 150*15 = 2250
        FIFO 消耗：100@10 (成本1000) + 50@12 (成本600) = 1600
        已实现盈亏 = 2250 - 1600 = 650
    剩余持仓：50股 @12，成本 600
    """
    pnl_service.invalidate_holdings_cache()
    s = _stock(session)
    _buy(session, s.id, date(2026, 1, 1), "100", "10")
    _buy(session, s.id, date(2026, 1, 2), "100", "12")
    _sell(session, s.id, date(2026, 1, 3), "150", "15")
    session.commit()

    h = pnl_service.compute_holding(session, s.id, use_cache=False)
    assert h.shares == Decimal("50")
    assert h.realized_pnl == Decimal("650")
    assert h.cost_basis == Decimal("600")
    assert h.avg_cost == Decimal("12")


def test_fifo_with_fees(session: Session) -> None:
    """带费用：买入费计入成本，卖出费抵减收入。

    买: 100 @10，费 5 → 单股成本 (1000+5)/100 = 10.05，成本基础 1005
    卖: 100 @11，费 5 → 收入 100*11 - 5 = 1095
        消耗成本 1005
        已实现盈亏 = 1095 - 1005 = 90
    剩余 0 股。
    """
    pnl_service.invalidate_holdings_cache()
    s = _stock(session, symbol="FEE")
    _buy(session, s.id, date(2026, 1, 1), "100", "10", fee="5")
    _sell(session, s.id, date(2026, 1, 2), "100", "11", fee="5")
    session.commit()

    h = pnl_service.compute_holding(session, s.id, use_cache=False)
    assert h.shares == Decimal("0")
    assert h.realized_pnl == Decimal("90")
    assert h.cost_basis == Decimal("0")


def test_split_2_for_1(session: Session) -> None:
    """持股100→1拆2：持股变200，单股成本减半，总成本不变。

    买: 100 @10 → 成本 1000，单股 10
    拆: 1拆2 (ratio 2/1) → 200股，单股 5，成本仍 1000
    """
    pnl_service.invalidate_holdings_cache()
    s = _stock(session, symbol="SPLIT")
    _buy(session, s.id, date(2026, 1, 1), "100", "10")
    session.add(
        CorporateAction(
            stock_id=s.id,
            action_type="SPLIT",
            ex_date=date(2026, 1, 5),
            ratio_num=Decimal("2"),
            ratio_den=Decimal("1"),
        )
    )
    session.commit()

    h = pnl_service.compute_holding(session, s.id, use_cache=False)
    assert h.shares == Decimal("200")
    assert h.cost_basis == Decimal("1000")
    assert h.avg_cost == Decimal("5")


def test_split_then_sell(session: Session) -> None:
    """拆股后卖出，已实现盈亏基于稀释后成本。

    买: 100 @20 → 成本2000
    拆: 1拆2 → 200股 @10，成本2000
    卖: 100 @15 → 收入1500，FIFO 消耗 100@10=1000 → 盈亏 500
    剩余 100股 @10，成本1000
    """
    pnl_service.invalidate_holdings_cache()
    s = _stock(session, symbol="SPS")
    _buy(session, s.id, date(2026, 1, 1), "100", "20")
    session.add(
        CorporateAction(
            stock_id=s.id,
            action_type="SPLIT",
            ex_date=date(2026, 1, 5),
            ratio_num=Decimal("2"),
            ratio_den=Decimal("1"),
        )
    )
    _sell(session, s.id, date(2026, 1, 10), "100", "15")
    session.commit()

    h = pnl_service.compute_holding(session, s.id, use_cache=False)
    assert h.shares == Decimal("100")
    assert h.realized_pnl == Decimal("500")
    assert h.cost_basis == Decimal("1000")


def test_unrealized_pnl(session: Session) -> None:
    """浮动盈亏 = 市值 - 成本。"""
    pnl_service.invalidate_holdings_cache()
    s = _stock(session, symbol="UPNL")
    _buy(session, s.id, date(2026, 1, 1), "100", "10")
    session.commit()
    h = pnl_service.compute_holding(session, s.id, use_cache=False)
    # 最新价 13 → 市值 1300，成本 1000 → 浮盈 300
    assert h.unrealized_pnl(Decimal("13")) == Decimal("300")
    assert h.market_value(Decimal("13")) == Decimal("1300")


def test_oversell_protection(session: Session) -> None:
    """超卖保护：卖出超过持仓时，盈亏只按实际持有部分计，不按零成本虚高。

    买: 100 @10 → 成本 1000
    卖: 150 @15 → 只能卖出 100 股（消耗成本 1000），收入按 100 股 = 1500
        已实现盈亏 = 1500 - 1000 = 500（不是按 150 股虚增）
        超卖 50 股记入 oversold_shares
    剩余持仓 0 股（不会变负）。
    """
    pnl_service.invalidate_holdings_cache()
    s = _stock(session, symbol="OVSL")
    _buy(session, s.id, date(2026, 1, 1), "100", "10")
    _sell(session, s.id, date(2026, 1, 2), "150", "15")
    session.commit()

    h = pnl_service.compute_holding(session, s.id, use_cache=False)
    assert h.shares == Decimal("0")
    assert h.realized_pnl == Decimal("500")
    assert h.cost_basis == Decimal("0")
    assert h.oversold_shares == Decimal("50")


def test_oversell_with_no_position(session: Session) -> None:
    """完全无持仓时卖出：不产生任何已实现盈亏，全部记为超卖。"""
    pnl_service.invalidate_holdings_cache()
    s = _stock(session, symbol="NAKED")
    _sell(session, s.id, date(2026, 1, 2), "100", "15")
    session.commit()

    h = pnl_service.compute_holding(session, s.id, use_cache=False)
    assert h.shares == Decimal("0")
    assert h.realized_pnl == Decimal("0")
    assert h.oversold_shares == Decimal("100")


def test_invalid_ratio_split_skipped_with_flag(session: Session) -> None:
    """ratio 为 0 的拆股被跳过，但记入 invalid_actions（不静默吞没）。

    买: 100 @10 → 持仓 100
    拆: ratio 0/1 → 无效，跳过，持仓仍 100，invalid_actions=1
    """
    pnl_service.invalidate_holdings_cache()
    s = _stock(session, symbol="BADR")
    _buy(session, s.id, date(2026, 1, 1), "100", "10")
    session.add(
        CorporateAction(
            stock_id=s.id,
            action_type="SPLIT",
            ex_date=date(2026, 1, 5),
            ratio_num=Decimal("0"),
            ratio_den=Decimal("1"),
        )
    )
    session.commit()

    h = pnl_service.compute_holding(session, s.id, use_cache=False)
    assert h.shares == Decimal("100")
    assert h.invalid_actions == 1
