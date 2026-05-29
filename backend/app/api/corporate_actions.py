"""公司行动 API（拆股/送股/配股/合并）。"""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlmodel import Session, select

from app.core.money import D, to_db_str
from app.core.response import Meta, ok
from app.database import get_session
from app.models.corporate_action import CorporateAction
from app.models.stock import Stock
from app.services.analysis import pnl as pnl_service

router = APIRouter(prefix="/corporate-actions", tags=["corporate-actions"])


class CorporateActionCreate(BaseModel):
    stock_id: int
    action_type: str  # SPLIT / BONUS / RIGHTS / MERGE
    ex_date: date
    ratio_num: str | None = None
    ratio_den: str | None = None
    subscribe_ratio: str | None = None
    subscribe_price: str | None = None
    notes: str | None = None


def _serialize(ca: CorporateAction) -> dict:
    return {
        "id": ca.id,
        "stock_id": ca.stock_id,
        "action_type": ca.action_type,
        "ex_date": ca.ex_date.isoformat(),
        "ratio_num": to_db_str(ca.ratio_num),
        "ratio_den": to_db_str(ca.ratio_den),
        "subscribe_ratio": to_db_str(ca.subscribe_ratio),
        "subscribe_price": to_db_str(ca.subscribe_price),
        "notes": ca.notes,
    }


@router.post("", summary="登记公司行动")
def create_action(payload: CorporateActionCreate, session: Session = Depends(get_session)) -> dict:
    if not session.get(Stock, payload.stock_id):
        raise HTTPException(status_code=404, detail="股票不存在")
    at = payload.action_type.upper()
    if at not in ("SPLIT", "BONUS", "RIGHTS", "MERGE"):
        raise HTTPException(status_code=422, detail="action_type 非法")
    # SPLIT/BONUS 必须有 ratio
    if at in ("SPLIT", "BONUS") and (not payload.ratio_num or not payload.ratio_den):
        raise HTTPException(status_code=422, detail="拆股/送股必须提供 ratio_num/ratio_den")

    ca = CorporateAction(
        stock_id=payload.stock_id,
        action_type=at,
        ex_date=payload.ex_date,
        ratio_num=D(payload.ratio_num) if payload.ratio_num else None,
        ratio_den=D(payload.ratio_den) if payload.ratio_den else None,
        subscribe_ratio=D(payload.subscribe_ratio) if payload.subscribe_ratio else None,
        subscribe_price=D(payload.subscribe_price) if payload.subscribe_price else None,
        notes=payload.notes,
    )
    session.add(ca)
    session.commit()
    session.refresh(ca)
    # 失效该股持仓缓存（公司行动影响持仓计算）
    pnl_service.invalidate_holdings_cache(payload.stock_id)
    return ok(_serialize(ca))


@router.get("", summary="公司行动列表")
def list_actions(
    stock_id: int | None = Query(None),
    session: Session = Depends(get_session),
) -> dict:
    stmt = select(CorporateAction)
    if stock_id:
        stmt = stmt.where(CorporateAction.stock_id == stock_id)
    stmt = stmt.order_by(CorporateAction.ex_date.desc())
    rows = list(session.exec(stmt).all())
    return ok([_serialize(r) for r in rows], meta=Meta(total=len(rows)))


@router.delete("/{action_id}", summary="删除公司行动")
def delete_action(action_id: int, session: Session = Depends(get_session)) -> dict:
    ca = session.get(CorporateAction, action_id)
    if not ca:
        raise HTTPException(status_code=404, detail="不存在")
    sid = ca.stock_id
    session.delete(ca)
    session.commit()
    pnl_service.invalidate_holdings_cache(sid)
    return ok({"deleted": action_id})
