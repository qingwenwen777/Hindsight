"""交易录入：强制日志 + 单事务 + 日志锁定测试。"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.core.journal_lock import JournalLockedError
from app.models.journal import Journal
from app.models.stock import Stock


def _make_stock(session: Session) -> int:
    stock = Stock(symbol="600519", market="CN", name="贵州茅台", currency="CNY")
    session.add(stock)
    session.commit()
    session.refresh(stock)
    return stock.id


def test_transaction_requires_journal(client: TestClient, session: Session) -> None:
    """缺少日志（thesis）→ 422。"""
    sid = _make_stock(session)
    # 完全不带 journal
    resp = client.post(
        "/api/v1/transactions",
        json={
            "stock_id": sid,
            "type": "BUY",
            "trade_date": "2026-01-02",
            "quantity": "100",
            "price": "1700",
            "currency": "CNY",
        },
    )
    assert resp.status_code == 422

    # 带 journal 但 thesis 为空 → 422
    resp2 = client.post(
        "/api/v1/transactions",
        json={
            "stock_id": sid,
            "type": "BUY",
            "trade_date": "2026-01-02",
            "quantity": "100",
            "price": "1700",
            "currency": "CNY",
            "journal": {"decision_type": "BUY", "thesis": ""},
        },
    )
    assert resp2.status_code == 422


def test_transaction_creates_locked_journal(client: TestClient, session: Session) -> None:
    """提交交易 → 自动建锁定 journal + 关联 transaction + 自动算费。"""
    sid = _make_stock(session)
    resp = client.post(
        "/api/v1/transactions",
        json={
            "stock_id": sid,
            "type": "BUY",
            "trade_date": "2026-01-02",
            "quantity": "100",
            "price": "1700",
            "currency": "CNY",
            "journal": {
                "decision_type": "BUY",
                "thesis": "护城河深，长期持有",
                "confidence": 4,
                "emotion": "CALM",
                "expected_horizon": "LONG",
            },
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 0
    assert body["message"] == "已记录"
    jid = body["data"]["journal_id"]
    assert jid is not None
    # 自动算费：A 股买 100*1700=170000 × 0.025% = 42.5（>5），过户 1.7
    assert body["data"]["fees"]["commission"] == "42.50"
    assert body["data"]["fees"]["other_fees"] == "1.70"

    # journal 应锁定
    j = session.get(Journal, jid)
    assert j is not None
    assert j.is_locked is True
    assert j.locked_at is not None


def test_locked_journal_cannot_be_modified(client: TestClient, session: Session) -> None:
    """已锁定 journal 的 UPDATE 被守卫拦截。"""
    sid = _make_stock(session)
    # 直接建一个锁定 journal
    j = Journal(
        stock_id=sid,
        decision_type="BUY",
        thesis="原始逻辑",
        is_locked=True,
    )
    session.add(j)
    session.commit()
    session.refresh(j)

    # 试图修改 thesis
    j.thesis = "事后篡改"
    raised = False
    try:
        session.commit()
    except JournalLockedError:
        raised = True
        session.rollback()
    assert raised, "修改已锁定 journal 应抛 JournalLockedError"


def test_add_review_does_not_touch_journal(client: TestClient, session: Session) -> None:
    """追加复盘是 INSERT，不修改锁定的 journal。"""
    sid = _make_stock(session)
    j = Journal(stock_id=sid, decision_type="BUY", thesis="逻辑", is_locked=True)
    session.add(j)
    session.commit()
    session.refresh(j)

    resp = client.post(
        f"/api/v1/journals/{j.id}/reviews",
        json={"review_date": "2026-02-01", "thesis_held": True, "lessons": "逻辑成立"},
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["thesis_held"] is True


def test_transaction_rejects_non_positive_quantity(client: TestClient, session: Session) -> None:
    """quantity <= 0 → 422。"""
    sid = _make_stock(session)
    resp = client.post(
        "/api/v1/transactions",
        json={
            "stock_id": sid,
            "type": "BUY",
            "trade_date": "2026-01-02",
            "quantity": "0",
            "price": "1700",
            "currency": "CNY",
            "journal": {"decision_type": "BUY", "thesis": "逻辑"},
        },
    )
    assert resp.status_code == 422


def test_transaction_rejects_future_date(client: TestClient, session: Session) -> None:
    """trade_date 为未来 → 422。"""
    sid = _make_stock(session)
    resp = client.post(
        "/api/v1/transactions",
        json={
            "stock_id": sid,
            "type": "BUY",
            "trade_date": "2099-01-02",
            "quantity": "100",
            "price": "1700",
            "currency": "CNY",
            "journal": {"decision_type": "BUY", "thesis": "逻辑"},
        },
    )
    assert resp.status_code == 422


def test_transaction_rejects_currency_mismatch(client: TestClient, session: Session) -> None:
    """交易币种与股票币种不一致 → 422。"""
    sid = _make_stock(session)  # 贵州茅台 CNY
    resp = client.post(
        "/api/v1/transactions",
        json={
            "stock_id": sid,
            "type": "BUY",
            "trade_date": "2026-01-02",
            "quantity": "100",
            "price": "1700",
            "currency": "USD",
            "journal": {"decision_type": "BUY", "thesis": "逻辑"},
        },
    )
    assert resp.status_code == 422


def test_transaction_rejects_invalid_currency(client: TestClient, session: Session) -> None:
    """非法币种 → 422。"""
    sid = _make_stock(session)
    resp = client.post(
        "/api/v1/transactions",
        json={
            "stock_id": sid,
            "type": "BUY",
            "trade_date": "2026-01-02",
            "quantity": "100",
            "price": "1700",
            "currency": "XYZ",
            "journal": {"decision_type": "BUY", "thesis": "逻辑"},
        },
    )
    assert resp.status_code == 422


def test_delete_transaction_with_cash_flow(client: TestClient, session: Session) -> None:
    """删除带现金流的导入交易：级联清理现金流，不抛 IntegrityError。"""
    from app.models.cash import CashAccount, CashFlow
    from app.models.journal import Journal as JournalModel
    from app.models.transaction import Transaction

    stock = Stock(symbol="7203", market="JP", name="トヨタ", currency="JPY")
    session.add(stock)
    acct = CashAccount(name="日股账户", currency="JPY")
    session.add(acct)
    session.commit()
    session.refresh(stock)
    session.refresh(acct)

    # 建占位 journal + 交易（模拟导入）
    j = JournalModel(stock_id=stock.id, decision_type="BUY", thesis="占位", is_imported=True)
    session.add(j)
    session.flush()
    tx = Transaction(
        stock_id=stock.id, type="BUY", trade_date=date(2026, 1, 2),
        quantity=Decimal("100"), price=Decimal("2000"), currency="JPY",
        journal_id=j.id, is_imported=True,
    )
    session.add(tx)
    session.flush()
    cf = CashFlow(
        account_id=acct.id, flow_date=date(2026, 1, 2), type="TRADE_BUY",
        amount=Decimal("-200000"), currency="JPY", related_tx_id=tx.id,
    )
    session.add(cf)
    session.commit()
    tx_id = tx.id
    j_id = j.id

    resp = client.delete(f"/api/v1/transactions/{tx_id}")
    assert resp.status_code == 200
    # 现金流与孤儿占位 journal 都被清理
    assert session.get(Transaction, tx_id) is None
    assert session.exec(
        select(CashFlow).where(CashFlow.related_tx_id == tx_id)
    ).first() is None
    assert session.get(JournalModel, j_id) is None
