"""规则筛选引擎测试 —— 确定性、运算符、AND、缺字段、百分比换算。"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlmodel import Session

from app.models.financials import Financial
from app.models.stock import Stock
from app.models.watchlist import Watchlist
from app.services.screener.engine import run_screen


def _stock(session: Session, symbol: str, market: str, name: str, industry: str | None = None) -> int:
    s = Stock(symbol=symbol, market=market, name=name, currency="USD", industry=industry)
    session.add(s)
    session.commit()
    session.refresh(s)
    return s.id


def _fin(session: Session, stock_id: int, **kw) -> None:
    f = Financial(stock_id=stock_id, as_of=date.today(), **kw)
    session.add(f)
    session.commit()


def test_numeric_and_combination(session: Session) -> None:
    a = _stock(session, "AAA", "US", "Alpha")
    b = _stock(session, "BBB", "US", "Beta")
    _fin(session, a, pe=Decimal("15"), revenue_yoy=Decimal("0.20"))  # PE15, 营收20%
    _fin(session, b, pe=Decimal("30"), revenue_yoy=Decimal("0.05"))

    # PE < 20 且 营收增速 > 15(%)
    conds = [
        {"field": "pe", "op": "<", "value": "20"},
        {"field": "revenue_yoy", "op": ">", "value": "15"},
    ]
    hits = run_screen(session, conds)
    assert [h.symbol for h in hits] == ["AAA"]
    assert hits[0].matched["revenue_yoy"] == "20.00%"


def test_missing_field_not_matched(session: Session) -> None:
    a = _stock(session, "AAA", "US", "Alpha")
    # 无 Financial 记录 → pe 缺失
    conds = [{"field": "pe", "op": "<", "value": "20"}]
    hits = run_screen(session, conds)
    assert hits == []
    # missing 通过单股查不到反映：用一个恒真布尔条件让它进候选再看 missing
    conds2 = [{"field": "in_watchlist", "op": "=", "value": False}, {"field": "pe", "op": "<", "value": "20"}]
    hits2 = run_screen(session, conds2)
    assert hits2 == []  # 仍不命中（pe 缺失）


def test_in_watchlist_filter(session: Session) -> None:
    a = _stock(session, "AAA", "US", "Alpha")
    _stock(session, "BBB", "US", "Beta")
    session.add(Watchlist(stock_id=a))
    session.commit()

    conds = [{"field": "in_watchlist", "op": "=", "value": True}]
    hits = run_screen(session, conds)
    assert [h.symbol for h in hits] == ["AAA"]


def test_between_operator(session: Session) -> None:
    a = _stock(session, "AAA", "US", "Alpha")
    _fin(session, a, pe=Decimal("18"))
    conds = [{"field": "pe", "op": "between", "value": "10", "value2": "20"}]
    assert [h.symbol for h in run_screen(session, conds)] == ["AAA"]
    conds2 = [{"field": "pe", "op": "between", "value": "20", "value2": "30"}]
    assert run_screen(session, conds2) == []


def test_market_filter_and_determinism(session: Session) -> None:
    _stock(session, "AAA", "US", "Alpha")
    _stock(session, "600519", "CN", "Moutai")
    conds = [{"field": "market", "op": "=", "value": "US"}]
    hits1 = run_screen(session, conds, markets=["US"])
    hits2 = run_screen(session, conds, markets=["US"])
    assert [h.symbol for h in hits1] == [h.symbol for h in hits2] == ["AAA"]
