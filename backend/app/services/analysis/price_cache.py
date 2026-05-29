"""行情 parquet 缓存（设计文档 7.4）。

把某股票的全量日线缓存为 parquet 文件，加速重复的历史区间查询。
交易/同步写入后应失效对应缓存。
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from sqlmodel import Session, select

from app.config import settings
from app.models.stock import Price


def _cache_dir() -> Path:
    d = settings.data_dir / "cache"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _cache_path(stock_id: int) -> Path:
    return _cache_dir() / f"prices_{stock_id}.parquet"


def invalidate_price_cache(stock_id: int) -> None:
    """失效某股票的 parquet 缓存。"""
    p = _cache_path(stock_id)
    if p.exists():
        p.unlink()


def load_prices_df(session: Session, stock_id: int) -> pd.DataFrame:
    """加载某股票全量日线为 DataFrame，优先读 parquet 缓存。

    缓存未命中则从 DB 读取并写入 parquet。
    列：date, open, high, low, close, volume（价格为 float，仅用于图表/指标）。
    """
    path = _cache_path(stock_id)
    if path.exists():
        try:
            return pd.read_parquet(path)
        except Exception:  # noqa: BLE001  缓存损坏则重建
            path.unlink(missing_ok=True)

    rows = session.exec(
        select(Price).where(Price.stock_id == stock_id).order_by(Price.date)
    ).all()
    data = [
        {
            "date": p.date.isoformat(),
            "open": float(p.open) if p.open is not None else None,
            "high": float(p.high) if p.high is not None else None,
            "low": float(p.low) if p.low is not None else None,
            "close": float(p.close),
            "volume": p.volume,
        }
        for p in rows
    ]
    df = pd.DataFrame(data)
    if not df.empty:
        try:
            df.to_parquet(path, index=False)
        except Exception:  # noqa: BLE001  缺 pyarrow 等则跳过缓存写入
            pass
    return df
