"""情绪审计统计（设计文档 F7.5）。

统计不同情绪下的买入交易后续表现：胜率、平均回报、盈亏比。
胜：买入后 30 天回报 > 0。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from sqlmodel import Session, select

from app.models.journal import Journal
from app.models.transaction import Transaction
from app.services.ai.context_builder import calc_return_pct

ZERO = Decimal("0")


@dataclass
class EmotionStat:
    emotion: str
    n: int = 0
    wins: int = 0
    total_return: Decimal = ZERO
    win_return: Decimal = ZERO
    loss_return: Decimal = ZERO

    @property
    def win_rate(self) -> float:
        return self.wins / self.n if self.n else 0.0

    @property
    def avg_return(self) -> Decimal:
        return self.total_return / self.n if self.n else ZERO

    @property
    def profit_loss_ratio(self) -> float | None:
        """盈亏比 = 平均盈利 / 平均亏损（绝对值）。"""
        losses = self.n - self.wins
        if self.wins == 0 or losses == 0:
            return None
        avg_win = self.win_return / self.wins
        avg_loss = abs(self.loss_return / losses)
        if avg_loss == 0:
            return None
        return float(avg_win / avg_loss)


def audit_emotions(
    session: Session, start: date | None = None, end: date | None = None
) -> list[EmotionStat]:
    """按情绪分组统计买入交易的后续表现。"""
    stmt = select(Transaction, Journal).where(
        Transaction.type == "BUY",
        Transaction.journal_id == Journal.id,
    )
    if start:
        stmt = stmt.where(Transaction.trade_date >= start)
    if end:
        stmt = stmt.where(Transaction.trade_date <= end)

    stats: dict[str, EmotionStat] = {}
    for tx, journal in session.exec(stmt).all():
        emotion = journal.emotion or "UNKNOWN"
        ret = calc_return_pct(session, tx.stock_id, tx.trade_date, 30)
        if ret is None:
            continue
        st = stats.setdefault(emotion, EmotionStat(emotion=emotion))
        st.n += 1
        st.total_return += ret
        if ret > 0:
            st.wins += 1
            st.win_return += ret
        else:
            st.loss_return += ret

    return sorted(stats.values(), key=lambda s: s.n, reverse=True)
