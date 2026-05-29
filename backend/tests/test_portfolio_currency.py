"""组合汇总跨币种换算测试。"""

from __future__ import annotations

from datetime import date

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.models.stock import Price, Stock
from app.models.transaction import Transaction
from app.services.data_sync.fx_client import upsert_fx_rate


def test_summary_multi_currency(client: TestClient, session: Session) -> None:
    """美股(USD)持仓按 JPY 汇总换算。

    买 10 股 @100 USD，成本 1000 USD。USD->JPY=150 → 150000 JPY。
    最新价 120 USD → 市值 1200 USD = 180000 JPY，浮盈 30000 JPY。
    """
    stock = Stock(symbol="AAPL", market="US", name="Apple", currency="USD")
    session.add(stock)
    session.commit()
    session.refresh(stock)

    session.add(
        Transaction(
            stock_id=stock.id,
            type="BUY",
            trade_date=date(2026, 5, 1),
            quantity="10",
            price="100",
            currency="USD",
            commission="0",
            tax="0",
            other_fees="0",
        )
    )
    session.add(
        Price(stock_id=stock.id, date=date(2026, 5, 10), close="120")
    )
    upsert_fx_rate(session, "USD", "JPY", date(2026, 5, 1), "150")
    session.commit()

    resp = client.get("/api/v1/portfolio/summary?currency=JPY")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["currency"] == "JPY"
    assert data["total_cost"] == "150000.00"
    assert data["total_market_value"] == "180000.00"
    assert data["total_unrealized_pnl"] == "30000.00"
