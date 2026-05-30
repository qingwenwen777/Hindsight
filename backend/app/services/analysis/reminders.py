"""复盘到期提醒（设计文档 F4.4 / 5.3）。

扫描已锁定日志，距决策日 30/60/90/180/365 天且该里程碑尚未复盘的，生成提醒。
按需计算（不常驻后台），前端铃铛与仪表盘调用。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from sqlmodel import Session, select

from app.models.journal import Journal, Review
from app.models.stock import Stock

# 复盘里程碑（天）
MILESTONES = [30, 60, 90, 180, 365]


@dataclass
class ReviewReminder:
    journal_id: int
    stock_id: int
    symbol: str
    name: str
    decision_type: str
    decision_date: str
    days_since: int
    due_milestone: int  # 命中的里程碑
    overdue_days: int  # 距该里程碑已过去多少天


def _decision_date(journal: Journal) -> date | None:
    """日志的决策日期：优先 locked_at，否则 created_at。"""
    dt = journal.locked_at or journal.created_at
    return dt.date() if dt else None


def compute_reminders(session: Session, as_of: date | None = None) -> list[ReviewReminder]:
    """计算所有到期复盘提醒。

    对每篇锁定日志，找已过去的最大里程碑，若该里程碑尚无对应 review 则提醒。
    """
    as_of = as_of or date.today()
    journals = list(session.exec(select(Journal).where(Journal.is_locked == True)).all())  # noqa: E712

    reminders: list[ReviewReminder] = []
    for j in journals:
        dd = _decision_date(j)
        if dd is None:
            continue
        days_since = (as_of - dd).days
        # 找已到期的里程碑（升序里取最大已达成的）
        due = [m for m in MILESTONES if days_since >= m]
        if not due:
            continue
        target_milestone = max(due)

        # 该日志已有的复盘里程碑（按 days_since_decision 近似匹配）
        reviews = session.exec(select(Review).where(Review.journal_id == j.id)).all()
        covered_milestones = set()
        for r in reviews:
            d = r.days_since_decision
            if d is None:
                continue
            # 命中最近的里程碑（容差 ±10 天）
            for m in MILESTONES:
                if abs(d - m) <= 10:
                    covered_milestones.add(m)

        if target_milestone in covered_milestones:
            continue

        stock = session.get(Stock, j.stock_id)
        reminders.append(
            ReviewReminder(
                journal_id=j.id,  # type: ignore[arg-type]
                stock_id=j.stock_id,
                symbol=stock.symbol if stock else "?",
                name=stock.name if stock else "?",
                decision_type=j.decision_type,
                decision_date=dd.isoformat(),
                days_since=days_since,
                due_milestone=target_milestone,
                overdue_days=days_since - target_milestone,
            )
        )

    # 越逾期越靠前
    reminders.sort(key=lambda r: r.overdue_days, reverse=True)
    return reminders
