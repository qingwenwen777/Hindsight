"""公司行动 API 测试：登记拆股后持仓反映乘法型变化。"""

from __future__ import annotations

from datetime import date

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.models.stock import Stock
from app.models.transaction import Transaction


def test_split_via_api_updates_holdings(client: TestClient, session: Session) -> None:
    """持股100 → API 登记 1拆2 → holdings 显示 200 股、成本不变。"""
    stock = Stock(symbol="AAPL", market="US", name="Apple", currency="USD")
    session.add(stock)
    session.commit()
    session.refresh(stock)

    # 买 100 @ 10（无费）
    session.add(
        Transaction(
            stock_id=stock.id,
            type="BUY",
            trade_date=date(2026, 1, 1),
            quantity="100",
            price="10",
            currency="USD",
            commission="0",
            tax="0",
            other_fees="0",
        )
    )
    session.commit()

    # 登记拆股
    resp = client.post(
        "/api/v1/corporate-actions",
        json={
            "stock_id": stock.id,
            "action_type": "SPLIT",
            "ex_date": "2026-01-05",
            "ratio_num": "2",
            "ratio_den": "1",
        },
    )
    assert resp.status_code == 200

    holdings = client.get("/api/v1/portfolio/holdings").json()["data"]
    pos = next(h for h in holdings if h["stock_id"] == stock.id)
    assert pos["shares"] == "200"
    assert pos["cost_basis"] == "1000.00"
    # 单股成本减半 5
    assert pos["avg_cost"] == "5.0000"


def test_split_requires_ratio(client: TestClient, session: Session) -> None:
    """拆股缺 ratio → 422。"""
    stock = Stock(symbol="X", market="US", name="X", currency="USD")
    session.add(stock)
    session.commit()
    session.refresh(stock)
    resp = client.post(
        "/api/v1/corporate-actions",
        json={"stock_id": stock.id, "action_type": "SPLIT", "ex_date": "2026-01-05"},
    )
    assert resp.status_code == 422
