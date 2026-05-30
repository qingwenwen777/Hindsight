"""复盘到期提醒测试。"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlmodel import Session

from app.models.journal import Journal, Review
from app.models.stock import Stock
from app.services.analysis.reminders import compute_reminders


def _stock(session: Session) -> int:
    s = Stock(symbol="600519", market="CN", name="贵州茅台", currency="CNY")
    session.add(s)
    session.commit()
    session.refresh(s)
    return s.id


def test_reminder_triggers_after_30d(session: Session) -> None:
    """锁定 40 天前的日志，未复盘 → 命中 30 天里程碑。"""
    sid = _stock(session)
    locked = datetime.now(timezone.utc) - timedelta(days=40)
    j = Journal(stock_id=sid, decision_type="BUY", thesis="t", is_locked=True, locked_at=locked)
    session.add(j)
    session.commit()

    reminders = compute_reminders(session)
    assert len(reminders) == 1
    assert reminders[0].due_milestone == 30
    assert reminders[0].days_since >= 40


def test_no_reminder_before_30d(session: Session) -> None:
    """锁定 10 天，未到任何里程碑 → 无提醒。"""
    sid = _stock(session)
    locked = datetime.now(timezone.utc) - timedelta(days=10)
    j = Journal(stock_id=sid, decision_type="BUY", thesis="t", is_locked=True, locked_at=locked)
    session.add(j)
    session.commit()
    assert compute_reminders(session) == []


def test_reminder_cleared_after_review(session: Session) -> None:
    """已对 30 天里程碑复盘 → 不再提醒该里程碑。"""
    sid = _stock(session)
    locked = datetime.now(timezone.utc) - timedelta(days=40)
    j = Journal(stock_id=sid, decision_type="BUY", thesis="t", is_locked=True, locked_at=locked)
    session.add(j)
    session.commit()
    session.refresh(j)
    # 添加一条 days_since_decision≈30 的复盘
    from datetime import date

    session.add(Review(journal_id=j.id, review_date=date.today(), days_since_decision=30))
    session.commit()

    assert compute_reminders(session) == []
