"""决策审计统计（信心校准 + 决策类别聚合）。

复用情绪审计同款口径：统计买入交易的后续 30 天表现。
胜：买入后 30 天回报 > 0。

- 信心校准（calibration）：按录入时的 confidence(1-5) 分组，对比"主观信心" vs
  "实际胜率"，揭示过度自信/信心不足。
- 决策类别聚合：按 thesis_category 分组，看哪类决策（价值/趋势/事件/成长）真正赚钱。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlmodel import Session, select

from app.models.journal import Journal
from app.models.transaction import Transaction
from app.services.ai.context_builder import calc_return_pct

ZERO = Decimal("0")

# confidence(1-5) 映射到"主观隐含胜率"，用于和实际胜率对比校准。
# 1=很没把握 ~ 5=很有把握，线性映射到 10%~90%。
_CONFIDENCE_IMPLIED = {1: 0.10, 2: 0.30, 3: 0.50, 4: 0.70, 5: 0.90}


@dataclass
class GroupStat:
    """单个分组（某信心级别 / 某类别）的统计。"""

    key: str
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
        losses = self.n - self.wins
        if self.wins == 0 or losses == 0:
            return None
        avg_win = self.win_return / self.wins
        avg_loss = abs(self.loss_return / losses)
        if avg_loss == 0:
            return None
        return float(avg_win / avg_loss)


def _collect(
    session: Session,
    key_fn,
    start: date | None,
    end: date | None,
) -> dict[str, GroupStat]:
    """按 key_fn(journal) 分组统计买入交易的 30 天后续表现。key_fn 返回 None 跳过。"""
    stmt = select(Transaction, Journal).where(
        Transaction.type == "BUY",
        Transaction.journal_id == Journal.id,
    )
    if start:
        stmt = stmt.where(Transaction.trade_date >= start)
    if end:
        stmt = stmt.where(Transaction.trade_date <= end)

    stats: dict[str, GroupStat] = {}
    for tx, journal in session.exec(stmt).all():
        key = key_fn(journal)
        if key is None:
            continue
        ret = calc_return_pct(session, tx.stock_id, tx.trade_date, 30)
        if ret is None:
            continue
        st = stats.setdefault(key, GroupStat(key=key))
        st.n += 1
        st.total_return += ret
        if ret > 0:
            st.wins += 1
            st.win_return += ret
        else:
            st.loss_return += ret
    return stats


@dataclass
class CalibrationRow:
    confidence: int
    implied_win_rate: float  # 主观隐含胜率
    actual_win_rate: float  # 实际胜率
    n: int
    avg_return: Decimal
    gap: float  # 实际 - 隐含（正=低估自己，负=过度自信）


def confidence_calibration(
    session: Session, start: date | None = None, end: date | None = None
) -> tuple[list[CalibrationRow], list[str]]:
    """信心校准：按 confidence(1-5) 分组，对比隐含胜率 vs 实际胜率。"""

    def key_fn(j: Journal) -> str | None:
        return str(j.confidence) if j.confidence in _CONFIDENCE_IMPLIED else None

    stats = _collect(session, key_fn, start, end)
    rows: list[CalibrationRow] = []
    for level in (1, 2, 3, 4, 5):
        st = stats.get(str(level))
        if not st or st.n == 0:
            continue
        implied = _CONFIDENCE_IMPLIED[level]
        actual = st.win_rate
        rows.append(
            CalibrationRow(
                confidence=level,
                implied_win_rate=implied,
                actual_win_rate=actual,
                n=st.n,
                avg_return=st.avg_return,
                gap=round(actual - implied, 4),
            )
        )

    # 结论：高信心(4-5)实际胜率明显低于隐含 → 过度自信
    conclusions: list[str] = []
    high = [r for r in rows if r.confidence >= 4 and r.n >= 3]
    for r in high:
        if r.gap < -0.2:
            conclusions.append(
                f"信心 {r.confidence}/5 的决策（{r.n} 笔）实际胜率仅 "
                f"{r.actual_win_rate * 100:.0f}%，明显低于自我预期，警惕过度自信。"
            )
    low = [r for r in rows if r.confidence <= 2 and r.n >= 3]
    for r in low:
        if r.gap > 0.2:
            conclusions.append(
                f"信心 {r.confidence}/5 的决策（{r.n} 笔）实际胜率达 "
                f"{r.actual_win_rate * 100:.0f}%，你可能低估了自己这类判断。"
            )
    return rows, conclusions


def category_aggregation(
    session: Session, start: date | None = None, end: date | None = None
) -> tuple[list[GroupStat], list[str]]:
    """决策类别聚合：按 thesis_category 分组统计胜率/平均回报/盈亏比。"""

    def key_fn(j: Journal) -> str | None:
        return j.thesis_category or "OTHER"

    stats = _collect(session, key_fn, start, end)
    rows = sorted(stats.values(), key=lambda s: s.n, reverse=True)

    conclusions: list[str] = []
    rated = [r for r in rows if r.n >= 3]
    if rated:
        best = max(rated, key=lambda r: r.avg_return)
        worst = min(rated, key=lambda r: r.avg_return)
        if best.key != worst.key:
            conclusions.append(
                f"你的「{best.key}」类决策表现最佳（平均 {best.avg_return:.1f}%，{best.n} 笔），"
                f"「{worst.key}」类最差（平均 {worst.avg_return:.1f}%，{worst.n} 笔）。"
            )
    return rows, conclusions
