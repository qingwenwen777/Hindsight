"""AI 洞察测试：日报上下文/降级、价格提醒去重、文档清理。"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from sqlmodel import Session

from app.models.insight import InsightDocument
from app.models.journal import Journal
from app.models.stock import Price, Stock
from app.models.watchlist import Watchlist


def _stock(session: Session, symbol="AAPL", market="US") -> int:
    s = Stock(symbol=symbol, market=market, name=symbol, currency="USD")
    session.add(s)
    session.commit()
    session.refresh(s)
    return s.id


def _price(session: Session, sid: int, d: date, close: str) -> None:
    session.add(Price(stock_id=sid, date=d, close=Decimal(close)))
    session.commit()


def test_daily_report_degraded_without_ai(session: Session, monkeypatch) -> None:
    """无 AI Key → 降级生成文档，degraded=True 且含数据。"""
    from app.services.ai import client as ai_client
    from app.services.insights import daily_report as dr

    sid = _stock(session)
    session.add(Watchlist(stock_id=sid))
    # 两日价格，制造 +10% 异动
    _price(session, sid, date(2026, 5, 28), "100")
    _price(session, sid, date(2026, 5, 29), "110")

    monkeypatch.setattr(ai_client, "is_available", lambda: False)
    doc = dr.build_daily_report(session, "US")
    assert doc.doc_type == "DAILY_REPORT"
    assert doc.degraded is True
    assert "异动" in doc.body_md or "AAPL" in doc.body_md


def test_daily_report_idempotent(session: Session, monkeypatch) -> None:
    """同市场同日多次生成不产生重复行。"""
    from app.services.ai import client as ai_client
    from app.services.insights import daily_report as dr

    sid = _stock(session)
    _price(session, sid, date(2026, 5, 28), "100")
    _price(session, sid, date(2026, 5, 29), "110")
    monkeypatch.setattr(ai_client, "is_available", lambda: False)

    d1 = dr.build_daily_report(session, "US", on_date=date(2026, 5, 29))
    d2 = dr.build_daily_report(session, "US", on_date=date(2026, 5, 29))
    assert d1.id == d2.id
    rows = list(session.exec(__import__("sqlmodel").select(InsightDocument)).all())
    assert len([r for r in rows if r.doc_type == "DAILY_REPORT"]) == 1


def test_price_alert_trigger_and_dedup(session: Session) -> None:
    """触及目标价生成提醒，重复评估不产生重复。"""
    from app.services.insights.price_alerts import evaluate_price_alerts

    sid = _stock(session)
    session.add(Watchlist(stock_id=sid))
    _price(session, sid, date(2026, 5, 29), "110")
    j = Journal(stock_id=sid, decision_type="BUY", thesis="t", target_price=Decimal("105"))
    session.add(j)
    session.commit()

    new1 = evaluate_price_alerts(session)
    assert len(new1) == 1
    assert new1[0].alert_type == "TARGET"
    # 再评估 → 去重，无新增
    new2 = evaluate_price_alerts(session)
    assert len(new2) == 0


def test_purge_old_documents(session: Session) -> None:
    """清理超 90 天文档，保留窗口内的。"""
    from app.services.insights.cleanup import purge_old_documents

    old = InsightDocument(doc_type="SCREENER_REVIEW", title="old", body_md="x")
    old.created_at = datetime.now(timezone.utc) - timedelta(days=100)
    fresh = InsightDocument(doc_type="SCREENER_REVIEW", title="fresh", body_md="y")
    fresh.created_at = datetime.now(timezone.utc) - timedelta(days=10)
    session.add(old)
    session.add(fresh)
    session.commit()

    removed = purge_old_documents(session, days=90)
    assert removed == 1
    remaining = list(session.exec(__import__("sqlmodel").select(InsightDocument)).all())
    assert len(remaining) == 1
    assert remaining[0].title == "fresh"


def test_empty_market_brief(session: Session, monkeypatch) -> None:
    """市场无标的 → 生成无重点事项简报，不报错。"""
    from app.services.ai import client as ai_client
    from app.services.insights import daily_report as dr

    monkeypatch.setattr(ai_client, "is_available", lambda: False)
    doc = dr.build_daily_report(session, "JP")
    assert doc is not None
    assert "无重点事项" in doc.body_md
