"""行情同步：校验 + UPSERT 幂等性测试（用 monkeypatch 避免真实网络）。"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from sqlmodel import Session, select

from app.models.stock import Price, Stock
from app.services.data_sync import sync_service
from app.services.data_sync.base import PriceBar, PriceValidationError, validate_bar


def test_validate_bar_rejects_high_lt_low() -> None:
    """high < low 应被拒绝。"""
    bar = PriceBar(
        date=date(2026, 1, 2),
        open=Decimal("10"),
        high=Decimal("9"),
        low=Decimal("11"),
        close=Decimal("10"),
    )
    with pytest.raises(PriceValidationError):
        validate_bar(bar)


def test_validate_bar_rejects_close_out_of_range() -> None:
    """close 超出 [low, high] 区间应被拒绝。"""
    bar = PriceBar(
        date=date(2026, 1, 2),
        open=Decimal("10"),
        high=Decimal("12"),
        low=Decimal("9"),
        close=Decimal("15"),
    )
    with pytest.raises(PriceValidationError):
        validate_bar(bar)


def _fake_bars() -> list[PriceBar]:
    return [
        PriceBar(date(2026, 1, 2), Decimal("100"), Decimal("105"), Decimal("99"), Decimal("103"), 1000),
        PriceBar(date(2026, 1, 3), Decimal("103"), Decimal("108"), Decimal("102"), Decimal("107"), 1200),
    ]


def test_upsert_idempotent(session: Session, monkeypatch) -> None:  # noqa: ANN001
    """重复同步不产生重复行（UPSERT）。"""
    stock = Stock(symbol="600519", market="CN", name="贵州茅台", currency="CNY")
    session.add(stock)
    session.commit()
    session.refresh(stock)

    # 用假数据替换网络拉取
    monkeypatch.setattr(sync_service, "fetch_cn_daily", lambda *a, **k: _fake_bars())

    # 第一次同步：2 行 insert
    r1 = sync_service.sync_stock_prices(session, stock, full=True)
    assert r1.ok
    assert r1.inserted == 2
    assert r1.updated == 0

    count1 = len(session.exec(select(Price).where(Price.stock_id == stock.id)).all())
    assert count1 == 2

    # 第二次同步：相同数据 → 2 行 update，仍是 2 行总数
    r2 = sync_service.sync_stock_prices(session, stock, full=True)
    assert r2.inserted == 0
    assert r2.updated == 2

    count2 = len(session.exec(select(Price).where(Price.stock_id == stock.id)).all())
    assert count2 == 2

    # 数据精确
    p = session.get(Price, (stock.id, date(2026, 1, 3)))
    assert p is not None
    assert p.close == Decimal("107")


def test_unsupported_market(session: Session) -> None:
    """非 A 股市场在 Step 1.3 返回不支持。"""
    stock = Stock(symbol="AAPL", market="US", name="Apple", currency="USD")
    session.add(stock)
    session.commit()
    session.refresh(stock)
    r = sync_service.sync_stock_prices(session, stock)
    assert not r.ok
    assert "暂不支持" in r.message
