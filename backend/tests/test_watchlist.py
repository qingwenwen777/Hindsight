"""关注列表测试：加入/去重/列表/取消。"""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.models.stock import Stock


def _stock(session: Session) -> int:
    s = Stock(symbol="600519", market="CN", name="贵州茅台", currency="CNY")
    session.add(s)
    session.commit()
    session.refresh(s)
    return s.id


def test_watchlist_crud(client: TestClient, session: Session) -> None:
    sid = _stock(session)

    # 加入
    r = client.post("/api/v1/watchlist", json={"stock_id": sid, "tags": ["白酒"]})
    assert r.status_code == 200
    assert r.json()["data"]["already"] is False

    # 重复加入 → already=True
    r2 = client.post("/api/v1/watchlist", json={"stock_id": sid})
    assert r2.json()["data"]["already"] is True

    # 列表
    lst = client.get("/api/v1/watchlist").json()
    assert lst["meta"]["total"] == 1
    assert lst["data"][0]["symbol"] == "600519"
    assert lst["data"][0]["tags"] == ["白酒"]

    # 取消
    d = client.delete(f"/api/v1/watchlist/{sid}")
    assert d.status_code == 200
    assert client.get("/api/v1/watchlist").json()["meta"]["total"] == 0


def test_watchlist_unknown_stock(client: TestClient) -> None:
    assert client.post("/api/v1/watchlist", json={"stock_id": 999}).status_code == 404
