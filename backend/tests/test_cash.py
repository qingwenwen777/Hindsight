"""现金账户与现金流测试：余额变动、交易自动现金流。"""

from __future__ import annotations

from decimal import Decimal

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.models.stock import Stock
from app.services.analysis import cash as cash_service


def test_deposit_withdraw_balance(client: TestClient, session: Session) -> None:
    """入金/出金后余额正确。"""
    acc = client.post(
        "/api/v1/portfolio/accounts",
        json={"name": "测试账户", "currency": "JPY"},
    ).json()["data"]
    aid = acc["id"]

    client.post("/api/v1/portfolio/cash-flows", json={"account_id": aid, "type": "DEPOSIT", "amount": "100000"})
    r = client.post(
        "/api/v1/portfolio/cash-flows",
        json={"account_id": aid, "type": "WITHDRAW", "amount": "-30000"},
    ).json()["data"]
    assert r["balance"] == "70000"


def test_trade_generates_cash_flow(client: TestClient, session: Session) -> None:
    """录入买入交易并关联账户 → 现金流出 = 成交额 + 费用。"""
    stock = Stock(symbol="600519", market="CN", name="贵州茅台", currency="CNY")
    session.add(stock)
    session.commit()
    session.refresh(stock)

    acc = client.post(
        "/api/v1/portfolio/accounts", json={"name": "A股账户", "currency": "CNY"}
    ).json()["data"]
    aid = acc["id"]
    client.post(
        "/api/v1/portfolio/cash-flows",
        json={"account_id": aid, "type": "DEPOSIT", "amount": "1000000"},
    )

    # 买 100 @ 1700 = 170000；A股佣金 170000*0.025%=42.5，过户 1.7 → 费 44.2
    # 现金流出 = -(170000 + 44.2) = -170044.2
    resp = client.post(
        "/api/v1/transactions",
        json={
            "stock_id": stock.id,
            "type": "BUY",
            "trade_date": "2026-01-02",
            "quantity": "100",
            "price": "1700",
            "currency": "CNY",
            "account_id": aid,
            "journal": {"decision_type": "BUY", "thesis": "长期持有逻辑"},
        },
    )
    assert resp.status_code == 200

    # 余额 = 1000000 - 170044.2 = 829955.8
    balance = cash_service.account_balance(session, aid)
    assert balance == Decimal("829955.8")

    flows = client.get(f"/api/v1/portfolio/cash-flows?account_id={aid}").json()["data"]
    trade_flow = [f for f in flows if f["type"] == "TRADE_BUY"]
    assert len(trade_flow) == 1
    assert trade_flow[0]["amount"] == "-170044.20"
    assert trade_flow[0]["related_tx_id"] is not None


def test_account_update_and_delete(client: TestClient, session: Session) -> None:
    """账户可改名、可删除（无交易关联时）。"""
    acc = client.post(
        "/api/v1/portfolio/accounts", json={"name": "旧名", "currency": "JPY"}
    ).json()["data"]
    aid = acc["id"]

    # 改名 + 改币种
    r = client.patch(f"/api/v1/portfolio/accounts/{aid}", json={"name": "新名", "currency": "USD"})
    assert r.status_code == 200
    assert r.json()["data"]["name"] == "新名"
    assert r.json()["data"]["currency"] == "USD"

    # 加一条手工入金后仍可删除（会清理手工流水）
    client.post("/api/v1/portfolio/cash-flows", json={"account_id": aid, "type": "DEPOSIT", "amount": "1000"})
    d = client.delete(f"/api/v1/portfolio/accounts/{aid}")
    assert d.status_code == 200
    assert client.get("/api/v1/portfolio/accounts").json()["meta"]["total"] == 0


def test_account_delete_blocked_when_trade_linked(client: TestClient, session: Session) -> None:
    """有交易关联现金流的账户不可直接删除（防丢账）。"""
    stock = Stock(symbol="600519", market="CN", name="贵州茅台", currency="CNY")
    session.add(stock)
    session.commit()
    session.refresh(stock)
    acc = client.post(
        "/api/v1/portfolio/accounts", json={"name": "A股", "currency": "CNY"}
    ).json()["data"]
    aid = acc["id"]
    client.post("/api/v1/portfolio/cash-flows", json={"account_id": aid, "type": "DEPOSIT", "amount": "1000000"})
    client.post(
        "/api/v1/transactions",
        json={
            "stock_id": stock.id,
            "type": "BUY",
            "trade_date": "2026-01-02",
            "quantity": "100",
            "price": "1700",
            "currency": "CNY",
            "account_id": aid,
            "journal": {"decision_type": "BUY", "thesis": "长期持有逻辑"},
        },
    )
    d = client.delete(f"/api/v1/portfolio/accounts/{aid}")
    assert d.status_code == 409
