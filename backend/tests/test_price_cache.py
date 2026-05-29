"""行情 parquet 缓存测试。"""

from __future__ import annotations

from datetime import date

from sqlmodel import Session

from app.models.stock import Price, Stock
from app.services.analysis import price_cache


def test_cache_roundtrip_and_invalidate(session: Session, tmp_path, monkeypatch) -> None:  # noqa: ANN001
    """加载 → 写缓存 → 命中 → 失效。"""
    # 把缓存目录指向临时目录
    monkeypatch.setattr(price_cache, "_cache_dir", lambda: tmp_path)

    s = Stock(symbol="T", market="CN", name="T", currency="CNY")
    session.add(s)
    session.commit()
    session.refresh(s)
    session.add(Price(stock_id=s.id, date=date(2026, 1, 2), close="10", open="9", high="11", low="8", volume=100))
    session.add(Price(stock_id=s.id, date=date(2026, 1, 3), close="12", open="10", high="13", low="9", volume=200))
    session.commit()

    df = price_cache.load_prices_df(session, s.id)
    assert len(df) == 2
    assert (tmp_path / f"prices_{s.id}.parquet").exists()

    # 第二次读取应命中缓存（即便删除 DB 行，缓存仍返回旧数据）
    for p in session.exec(__import__("sqlmodel").select(Price)).all():
        session.delete(p)
    session.commit()
    df2 = price_cache.load_prices_df(session, s.id)
    assert len(df2) == 2  # 命中缓存

    # 失效后重建（DB 已空 → 空 df）
    price_cache.invalidate_price_cache(s.id)
    df3 = price_cache.load_prices_df(session, s.id)
    assert df3.empty
