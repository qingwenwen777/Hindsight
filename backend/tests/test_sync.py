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

    # 用假数据替换数据源分派
    monkeypatch.setattr(sync_service, "_fetch_via_source", lambda *a, **k: _fake_bars())

    # 第一次同步：2 行 insert
    r1 = sync_service.sync_stock_prices(session, stock, full=True, write_log=False)
    assert r1.ok
    assert r1.inserted == 2
    assert r1.updated == 0

    count1 = len(session.exec(select(Price).where(Price.stock_id == stock.id)).all())
    assert count1 == 2

    # 第二次同步：相同数据 → 2 行 update，仍是 2 行总数
    r2 = sync_service.sync_stock_prices(session, stock, full=True, write_log=False)
    assert r2.inserted == 0
    assert r2.updated == 2

    count2 = len(session.exec(select(Price).where(Price.stock_id == stock.id)).all())
    assert count2 == 2

    # 数据精确
    p = session.get(Price, (stock.id, date(2026, 1, 3)))
    assert p is not None
    assert p.close == Decimal("107")


def test_fallback_chain(session: Session, monkeypatch) -> None:  # noqa: ANN001
    """A 股首选 akshare 失败时回退 yfinance。"""
    from app.services.data_sync import sync_service as svc

    stock = Stock(symbol="600519", market="CN", name="贵州茅台", currency="CNY")
    session.add(stock)
    session.commit()
    session.refresh(stock)

    # akshare 抛不可用，yfinance 返回数据
    def _fake_dispatch(source, stk, start):  # noqa: ANN001
        from app.services.data_sync.akshare_client import AkShareUnavailable

        if source == "akshare":
            raise AkShareUnavailable("模拟 akshare 不可用")
        return _fake_bars()

    monkeypatch.setattr(svc, "_fetch_via_source", _fake_dispatch)
    r = svc.sync_stock_prices(session, stock, full=True, write_log=False)
    assert r.ok
    assert r.source == "yfinance"
    assert r.inserted == 2


def test_all_sources_fail(session: Session, monkeypatch) -> None:  # noqa: ANN001
    """所有数据源失败 → 标记失败。"""
    from app.services.data_sync import sync_service as svc
    from app.services.data_sync.akshare_client import AkShareUnavailable
    from app.services.data_sync.yfinance_client import YFinanceUnavailable

    stock = Stock(symbol="AAPL", market="US", name="Apple", currency="USD")
    session.add(stock)
    session.commit()
    session.refresh(stock)

    def _all_fail(source, stk, start):  # noqa: ANN001
        if source == "akshare":
            raise AkShareUnavailable("no")
        raise YFinanceUnavailable("no")

    monkeypatch.setattr(svc, "_fetch_via_source", _all_fail)
    r = svc.sync_stock_prices(session, stock, full=True, write_log=False)
    assert not r.ok
    assert "所有数据源失败" in r.message


def test_validate_bar_clamps_rounding_overshoot() -> None:
    """前复权舍入导致 close 略高于 high（<0.5%）→ 钳制到 high，不丢弃。"""
    bar = PriceBar(
        date=date(2003, 1, 2),
        open=Decimal("12.00"),
        high=Decimal("12.50"),
        low=Decimal("11.80"),
        close=Decimal("12.53"),  # 比 high 高 0.24%，舍入误差
    )
    validate_bar(bar)  # 不抛错
    assert bar.close == Decimal("12.50")  # 钳到上界


def test_validate_bar_clamps_open_below_low() -> None:
    """open 略低于 low（舍入）→ 钳到 low。"""
    bar = PriceBar(
        date=date(2003, 1, 2),
        open=Decimal("9.97"),
        high=Decimal("10.50"),
        low=Decimal("10.00"),
        close=Decimal("10.20"),
    )
    validate_bar(bar)
    assert bar.open == Decimal("10.00")
