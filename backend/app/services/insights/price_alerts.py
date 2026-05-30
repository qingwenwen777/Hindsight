"""价格提醒 —— 持仓∪关注标的触及目标价/止损价时生成提醒（去重）。"""

from __future__ import annotations

from decimal import Decimal

from sqlmodel import Session, select

from app.core.money import D, to_db_str
from app.logging_config import get_logger
from app.models.insight import PriceAlert
from app.models.journal import Journal
from app.models.stock import Price, Stock
from app.models.watchlist import Watchlist

log = get_logger(__name__)


def _latest_close(session: Session, stock_id: int) -> Decimal | None:
    row = session.exec(
        select(Price.close).where(Price.stock_id == stock_id).order_by(Price.date.desc()).limit(1)
    ).first()
    return D(row) if row is not None else None


def _candidate_stock_ids(session: Session) -> set[int]:
    """持仓 ∪ 关注。"""
    from app.services.analysis.pnl import compute_all_holdings

    ids: set[int] = {ph.stock.id for ph in compute_all_holdings(session)}  # type: ignore[misc]
    ids |= set(session.exec(select(Watchlist.stock_id)).all())
    return ids


def _latest_journal_with_targets(session: Session, stock_id: int) -> Journal | None:
    rows = session.exec(
        select(Journal).where(Journal.stock_id == stock_id).order_by(Journal.created_at.desc())
    ).all()
    for j in rows:
        if j.target_price is not None or j.stop_loss_price is not None:
            return j
    return None


def evaluate_price_alerts(session: Session) -> list[PriceAlert]:
    """评估并写入新触发的价格提醒。返回新建的提醒列表。"""
    new_alerts: list[PriceAlert] = []
    existing_keys = set(session.exec(select(PriceAlert.dedup_key)).all())

    for sid in _candidate_stock_ids(session):
        last = _latest_close(session, sid)
        if last is None:
            continue
        j = _latest_journal_with_targets(session, sid)
        if j is None:
            continue

        checks: list[tuple[str, Decimal]] = []
        if j.target_price is not None and last >= D(j.target_price):
            checks.append(("TARGET", D(j.target_price)))
        if j.stop_loss_price is not None and last <= D(j.stop_loss_price):
            checks.append(("STOP", D(j.stop_loss_price)))

        for alert_type, threshold in checks:
            dedup_key = f"{sid}:{alert_type}:{to_db_str(threshold)}"
            if dedup_key in existing_keys:
                continue
            alert = PriceAlert(
                stock_id=sid,
                journal_id=j.id,
                alert_type=alert_type,
                threshold=threshold,
                triggered_price=last,
                dedup_key=dedup_key,
            )
            session.add(alert)
            new_alerts.append(alert)
            existing_keys.add(dedup_key)

    if new_alerts:
        session.commit()
        for a in new_alerts:
            session.refresh(a)
        log.info("price_alerts.new", count=len(new_alerts))
    return new_alerts


def list_alerts(session: Session, limit: int = 50) -> list[dict]:
    """列出价格提醒（未读优先，按触发时间倒序），含股票信息。"""
    rows = session.exec(
        select(PriceAlert).order_by(PriceAlert.is_read, PriceAlert.triggered_at.desc()).limit(limit)
    ).all()
    out: list[dict] = []
    for a in rows:
        stock = session.get(Stock, a.stock_id)
        out.append(
            {
                "id": a.id,
                "stock_id": a.stock_id,
                "journal_id": a.journal_id,
                "symbol": stock.symbol if stock else "?",
                "name": stock.name if stock else "?",
                "alert_type": a.alert_type,
                "threshold": to_db_str(a.threshold),
                "triggered_price": to_db_str(a.triggered_price),
                "is_read": a.is_read,
                "triggered_at": a.triggered_at.isoformat() if a.triggered_at else None,
            }
        )
    return out


__all__ = ["evaluate_price_alerts", "list_alerts"]
