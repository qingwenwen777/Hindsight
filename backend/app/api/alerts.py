"""价格提醒 API：列表 / 标记已读 / 手动评估。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select

from app.core.response import Meta, ok
from app.database import get_session
from app.models.insight import PriceAlert
from app.services.insights.price_alerts import evaluate_price_alerts, list_alerts

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("/price", summary="价格提醒列表")
def price_alerts(
    limit: int = Query(50, le=200),
    session: Session = Depends(get_session),
) -> dict:
    data = list_alerts(session, limit=limit)
    unread = sum(1 for a in data if not a["is_read"])
    return ok(data, meta=Meta(total=len(data), page=unread))  # page 复用为未读数


@router.get("/price/unread-count", summary="未读价格提醒数")
def unread_count(session: Session = Depends(get_session)) -> dict:
    rows = session.exec(select(PriceAlert).where(PriceAlert.is_read == False)).all()  # noqa: E712
    return ok({"count": len(rows)})


@router.post("/price/{alert_id}/read", summary="标记价格提醒已读")
def mark_read(alert_id: int, session: Session = Depends(get_session)) -> dict:
    alert = session.get(PriceAlert, alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="提醒不存在")
    alert.is_read = True
    session.add(alert)
    session.commit()
    return ok({"id": alert_id, "is_read": True})


@router.post("/price/evaluate", summary="手动评估价格提醒")
def evaluate(session: Session = Depends(get_session)) -> dict:
    new = evaluate_price_alerts(session)
    return ok({"new": len(new)})
