"""持有时间警告（设计文档 F7.3）。

声明 LONG 但 < 30 天就卖出 → 触发警告，要求填"为什么改主意"。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from sqlmodel import Session, select

from app.models.journal import Journal
from app.models.transaction import Transaction

# 各 horizon 的最短"名义"持有天数
HORIZON_MIN_DAYS = {
    "SHORT": 0,
    "MEDIUM": 30,
    "LONG": 90,
}

# LONG 声明下，< 此天数卖出即警告
LONG_EARLY_SELL_DAYS = 30


@dataclass
class HoldingTimeWarning:
    triggered: bool
    declared_horizon: str | None
    held_days: int | None
    reason: str


def check_early_sell(
    session: Session, stock_id: int, sell_date: date
) -> HoldingTimeWarning:
    """检查某股票在 sell_date 卖出是否过早（相对其最近一次买入日志声明的 horizon）。"""
    # 找该股最近一次有 LONG/MEDIUM 声明的买入日志
    buy = session.exec(
        select(Transaction)
        .where(Transaction.stock_id == stock_id, Transaction.type == "BUY")
        .order_by(Transaction.trade_date.desc())
    ).first()
    if not buy:
        return HoldingTimeWarning(False, None, None, "无买入记录")

    journal = session.get(Journal, buy.journal_id) if buy.journal_id else None
    horizon = journal.expected_horizon if journal else None
    held_days = (sell_date - buy.trade_date).days

    if horizon == "LONG" and held_days < LONG_EARLY_SELL_DAYS:
        return HoldingTimeWarning(
            True,
            horizon,
            held_days,
            f"声明长期持有(LONG)，但仅持有 {held_days} 天就卖出（< {LONG_EARLY_SELL_DAYS} 天）。"
            "请记录为什么改主意。",
        )
    return HoldingTimeWarning(False, horizon, held_days, "持有时间符合预期")
