"""财务/估值指标测试：存取 + API。"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.models.financials import Financial
from app.models.stock import Stock


def _stock(session: Session) -> int:
    s = Stock(symbol="AAPL", market="US", name="Apple", currency="USD")
    session.add(s)
    session.commit()
    session.refresh(s)
    return s.id


def test_financials_endpoint(client: TestClient, session: Session) -> None:
    sid = _stock(session)
    session.add(
        Financial(
            stock_id=sid,
            as_of=date(2026, 5, 1),
            pe=Decimal("28.5"),
            pb=Decimal("45.2"),
            roe=Decimal("1.45"),
            revenue_yoy=Decimal("0.08"),
            profit_yoy=Decimal("0.12"),
            source="test",
        )
    )
    session.commit()

    r = client.get(f"/api/v1/stocks/{sid}/financials")
    assert r.status_code == 200
    d = r.json()["data"]
    assert d["pe"] == "28.5"
    assert d["revenue_yoy"] == "0.08"
    assert d["source"] == "test"


def test_financials_none_when_absent(client: TestClient, session: Session) -> None:
    sid = _stock(session)
    r = client.get(f"/api/v1/stocks/{sid}/financials")
    assert r.status_code == 200
    assert r.json()["data"] is None


def test_ai_context_includes_financials(session: Session) -> None:
    """AI 交易复盘上下文应包含财务数据。"""
    from datetime import date as d

    from app.models.journal import Journal
    from app.models.transaction import Transaction
    from app.services.ai.context_builder import build_trade_review_context

    sid = _stock(session)
    session.add(
        Financial(stock_id=sid, as_of=d(2026, 5, 1), pe=Decimal("28.5"), roe=Decimal("1.45"))
    )
    j = Journal(stock_id=sid, decision_type="BUY", thesis="逻辑", is_locked=True)
    session.add(j)
    session.commit()
    session.refresh(j)
    tx = Transaction(
        stock_id=sid, type="BUY", trade_date=d(2026, 1, 2), quantity="10", price="180",
        currency="USD", journal_id=j.id, commission="0", tax="0", other_fees="0",
    )
    session.add(tx)
    session.commit()

    ctx = build_trade_review_context(session, tx.id)
    assert "PE: 28.5" in ctx
    assert "财务/估值数据" in ctx
