"""持仓与 FIFO 盈亏计算（Step 1.5 实现完整逻辑）。

当前先提供缓存失效占位，供交易写入时调用；完整 FIFO 在 Step 1.5 补齐。
"""

from __future__ import annotations

# 进程内持仓缓存（stock_id -> 计算结果）。Step 6 可换成更完善的缓存。
_holdings_cache: dict[int, object] = {}


def invalidate_holdings_cache(stock_id: int | None = None) -> None:
    """失效持仓缓存。stock_id 为空则清空全部。"""
    if stock_id is None:
        _holdings_cache.clear()
    else:
        _holdings_cache.pop(stock_id, None)
