"""组合 API 闭环测试：录入交易 → 持仓出现。"""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.models.stock import Stock


def _make_stock(session: Session) -> int:
    stock = Stock(symbol="600519", market="CN", name="贵州茅台", currency="CNY")
    session.add(stock)
    session.commit()
    session.refresh(stock)
    return stock.id


def test_record_then_holdings(client: TestClient, session: Session) -> None:
    """录入一笔买入后，/portfolio/holdings 能看到持仓。"""
    sid = _make_stock(session)
    resp = client.post(
        "/api/v1/transactions",
        json={
            "stock_id": sid,
            "type": "BUY",
            "trade_date": "2026-01-02",
            "quantity": "100",
            "price": "10",
            "currency": "CNY",
            "commission": "0",
            "tax": "0",
            "other_fees": "0",
            "journal": {"decision_type": "BUY", "thesis": "测试买入逻辑"},
        },
    )
    assert resp.status_code == 200

    holdings = client.get("/api/v1/portfolio/holdings").json()
    assert holdings["code"] == 0
    assert holdings["meta"]["total"] == 1
    pos = holdings["data"][0]
    assert pos["symbol"] == "600519"
    assert pos["shares"] == "100"
    assert pos["cost_basis"] == "1000.00"

    summary = client.get("/api/v1/portfolio/summary?currency=CNY").json()
    assert summary["data"]["positions"] == 1
    assert summary["data"]["total_cost"] == "1000.00"
