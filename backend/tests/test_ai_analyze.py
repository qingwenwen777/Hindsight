"""AI 分析端到端：交易复盘生成 + 写缓存 + 重复请求命中缓存。"""

from __future__ import annotations

from datetime import date

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.models.ai_insight import AiInsight
from app.models.journal import Journal
from app.models.stock import Price, Stock
from app.models.transaction import Transaction
from app.services.ai import client as ai_client
from app.services.ai import providers as ai_providers
from app.services.ai.providers import LlmResult, ResolvedProvider


def _fake_provider(monkeypatch, model: str = "claude-sonnet-4-5") -> None:
    """让 providers.resolve 返回一个固定服务商，providers.call 返回假回复。"""
    rp = ResolvedProvider(
        protocol="anthropic", base_url=None, api_key="test-key",
        model=model, provider_id=None, provider_name="test",
    )
    monkeypatch.setattr(ai_providers, "resolve", lambda *a, **k: rp)
    monkeypatch.setattr(
        ai_providers,
        "call",
        lambda rp_, **k: LlmResult(
            text="1. 逻辑部分成立。2. 更多源自判断力。3. 留意确认偏误。",
            model=rp_.model, prompt_tokens=500, completion_tokens=200,
        ),
    )


def _setup_trade(session: Session) -> int:
    stock = Stock(symbol="600519", market="CN", name="贵州茅台", currency="CNY")
    session.add(stock)
    session.commit()
    session.refresh(stock)
    journal = Journal(
        stock_id=stock.id, decision_type="BUY", thesis="护城河深", is_locked=True,
        confidence=4, emotion="CALM", expected_horizon="LONG",
    )
    session.add(journal)
    session.commit()
    session.refresh(journal)
    tx = Transaction(
        stock_id=stock.id, type="BUY", trade_date=date(2026, 1, 2),
        quantity="100", price="1700", currency="CNY", journal_id=journal.id,
        commission="0", tax="0", other_fees="0",
    )
    session.add(tx)
    # 30 天后价格用于回报计算
    session.add(Price(stock_id=stock.id, date=date(2026, 1, 2), close="1700"))
    session.add(Price(stock_id=stock.id, date=date(2026, 2, 1), close="1870"))
    session.commit()
    return tx.id


def test_trade_review_generates_and_caches(
    client: TestClient, session: Session, monkeypatch
) -> None:  # noqa: ANN001
    """生成复盘 → 写缓存；再次请求命中缓存不新增记录。"""
    tx_id = _setup_trade(session)

    # 模拟有服务商 + 假回复
    _fake_provider(monkeypatch)

    r1 = client.post("/api/v1/ai/analyze", json={"type": "TRADE_REVIEW", "target_id": tx_id})
    assert r1.status_code == 200
    d1 = r1.json()["data"]
    assert d1["cached"] is False
    assert d1["degraded"] is False
    assert "仅供参考" in d1["response"]
    assert int(d1["prompt_tokens"]) == 500

    # 缓存应有 1 条
    assert len(session.exec(select(AiInsight)).all()) == 1

    # 第二次相同请求 → 命中缓存，不新增
    r2 = client.post("/api/v1/ai/analyze", json={"type": "TRADE_REVIEW", "target_id": tx_id})
    assert r2.json()["data"]["cached"] is True
    assert len(session.exec(select(AiInsight)).all()) == 1


def test_budget_endpoint(client: TestClient) -> None:
    """预算端点返回结构正确。"""
    resp = client.get("/api/v1/ai/budget")
    assert resp.status_code == 200
    d = resp.json()["data"]
    assert "monthly_budget_jpy" in d
    assert "used_jpy" in d
    assert "usage_ratio" in d


def test_analyze_degraded_without_key(client: TestClient, session: Session, monkeypatch) -> None:  # noqa: ANN001
    """无服务商 → analyze 返回 degraded。"""
    tx_id = _setup_trade(session)
    from app.services.ai import providers as _p

    monkeypatch.setattr(_p, "resolve", lambda *a, **k: None)
    resp = client.post("/api/v1/ai/analyze", json={"type": "TRADE_REVIEW", "target_id": tx_id})
    assert resp.status_code == 200
    assert resp.json()["data"]["degraded"] is True
