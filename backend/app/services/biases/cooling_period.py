"""冷静期与复仇交易检测（设计文档 5.6 / F7）。

- 普通买卖：30 秒冷静期（前端倒计时，后端不强制时长，仅提供检测）。
- 复仇交易：对同一股票连续 3 次亏损后又买入 → 冷静期延长到 5 分钟 + AI 确认。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from sqlmodel import Session, select

from app.models.journal import Journal
from app.models.stock import Stock
from app.models.transaction import Transaction
from app.services.ai.context_builder import calc_return_pct

NORMAL_COOLDOWN_SECONDS = 30
REVENGE_COOLDOWN_SECONDS = 300  # 5 分钟
REVENGE_LOSS_STREAK = 3
REVENGE_LOSS_THRESHOLD_PCT = 0  # 亏损（回报 < 0）即计入连亏


@dataclass
class CooldownDecision:
    """冷静期判定结果。"""

    seconds: int
    is_revenge: bool
    require_ai_confirm: bool
    reason: str


def detect_revenge_trade(
    session: Session, stock_id: int, as_of: date | None = None
) -> CooldownDecision:
    """检测是否为复仇交易。

    口径：该股票最近的若干笔 BUY 交易，若其后 30 天回报连续 3 次为负，
    则下一次买入判定为复仇交易，延长冷静期并要求 AI 确认。
    """
    txs = list(
        session.exec(
            select(Transaction)
            .where(Transaction.stock_id == stock_id, Transaction.type == "BUY")
            .order_by(Transaction.trade_date.desc())
        ).all()
    )
    streak = 0
    for tx in txs:
        ret = calc_return_pct(session, stock_id, tx.trade_date, 30)
        if ret is None:
            break
        if ret < REVENGE_LOSS_THRESHOLD_PCT:
            streak += 1
            if streak >= REVENGE_LOSS_STREAK:
                break
        else:
            break

    if streak >= REVENGE_LOSS_STREAK:
        return CooldownDecision(
            seconds=REVENGE_COOLDOWN_SECONDS,
            is_revenge=True,
            require_ai_confirm=True,
            reason=f"该股最近连续 {streak} 笔买入后 30 天为亏损，疑似复仇交易",
        )
    return CooldownDecision(
        seconds=NORMAL_COOLDOWN_SECONDS,
        is_revenge=False,
        require_ai_confirm=False,
        reason="正常冷静期",
    )
