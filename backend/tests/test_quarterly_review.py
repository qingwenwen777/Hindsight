"""AI 季度模式分析测试（faked AI）。"""

from __future__ import annotations

from datetime import date, timedelta

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.models.journal import Journal
from app.models.stock import Price, Stock
from app.models.transaction import Transaction
from app.services.ai import client as ai_client


class _Usage:
    input_tokens = 800
    output_tokens = 300


class _Block:
    type = "text"
    text = "模式1：FOMO 情绪下买入胜率低。支持交易：见列表。改进：建立买入检查清单。"


class _Msg:
    content = [_Block()]
    usage = _Usage()


class _Messages:
    def create(self, **kwargs):  # noqa: ANN003
        return _Msg()


class _Client:
    def __init__(self, *a, **k):  # noqa: ANN002, ANN003
        self.messages = _Messages()


def test_quarterly_review(client: TestClient, session: Session, monkeypatch) -> None:  # noqa: ANN001
    """季度模式分析返回 AI 文本 + 支撑交易。"""
    s = Stock(symbol="600519", market="CN", name="茅台", currency="CNY")
    session.add(s)
    session.commit()
    session.refresh(s)
    j = Journal(stock_id=s.id, decision_type="BUY", thesis="t", emotion="FOMO", is_locked=True)
    session.add(j)
    session.commit()
    session.refresh(j)
    buy_d = date(2026, 1, 15)  # Q1
    session.add(
        Transaction(
            stock_id=s.id, type="BUY", trade_date=buy_d, quantity="100", price="100",
            currency="CNY", journal_id=j.id, commission="0", tax="0", other_fees="0",
        )
    )
    session.add(Price(stock_id=s.id, date=buy_d, close="100"))
    session.add(Price(stock_id=s.id, date=buy_d + timedelta(days=30), close="80"))
    session.commit()

    monkeypatch.setattr(ai_client, "is_available", lambda: True)
    monkeypatch.setattr(ai_client.settings, "anthropic_api_key", "k")
    import anthropic

    monkeypatch.setattr(anthropic, "Anthropic", _Client)

    resp = client.post("/api/v1/ai/quarterly-review?year=2026&quarter=1")
    assert resp.status_code == 200
    d = resp.json()["data"]
    assert d["period"] == "2026Q1"
    assert "FOMO" in d["response"]
    assert "仅供参考" in d["response"]
    assert len(d["supporting_transactions"]) == 1
    assert d["supporting_transactions"][0]["symbol"] == "600519"
