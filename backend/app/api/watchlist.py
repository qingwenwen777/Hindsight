"""关注列表 API。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from app.core.money import to_db_str
from app.core.response import Meta, ok
from app.database import get_session
from app.models.stock import Price, Stock
from app.models.watchlist import Watchlist

router = APIRouter(prefix="/watchlist", tags=["watchlist"])


class WatchlistAdd(BaseModel):
    stock_id: int
    notes: str | None = None
    tags: list[str] | None = None


def _latest_close(session: Session, stock_id: int):  # noqa: ANN201
    row = session.exec(
        select(Price.close).where(Price.stock_id == stock_id).order_by(Price.date.desc()).limit(1)
    ).first()
    return row


@router.get("", summary="关注列表")
def list_watchlist(session: Session = Depends(get_session)) -> dict:
    """返回关注的股票（含最新价）。"""
    rows = list(session.exec(select(Watchlist).order_by(Watchlist.added_at.desc())).all())
    data = []
    for w in rows:
        stock = session.get(Stock, w.stock_id)
        if not stock:
            continue
        data.append(
            {
                "id": w.id,
                "stock_id": w.stock_id,
                "symbol": stock.symbol,
                "market": stock.market,
                "name": stock.name,
                "currency": stock.currency,
                "last_price": to_db_str(_latest_close(session, w.stock_id)),
                "notes": w.notes,
                "tags": w.tags,
                "added_at": w.added_at.isoformat() if w.added_at else None,
            }
        )
    return ok(data, meta=Meta(total=len(data)))


@router.post("", summary="加入关注")
def add_watchlist(payload: WatchlistAdd, session: Session = Depends(get_session)) -> dict:
    if not session.get(Stock, payload.stock_id):
        raise HTTPException(status_code=404, detail="股票不存在")
    existing = session.exec(
        select(Watchlist).where(Watchlist.stock_id == payload.stock_id)
    ).first()
    if existing:
        return ok({"id": existing.id, "already": True})
    w = Watchlist(stock_id=payload.stock_id, notes=payload.notes, tags=payload.tags)
    session.add(w)
    session.commit()
    session.refresh(w)
    return ok({"id": w.id, "already": False})


@router.delete("/{stock_id}", summary="取消关注")
def remove_watchlist(stock_id: int, session: Session = Depends(get_session)) -> dict:
    w = session.exec(select(Watchlist).where(Watchlist.stock_id == stock_id)).first()
    if not w:
        raise HTTPException(status_code=404, detail="未在关注列表")
    session.delete(w)
    session.commit()
    return ok({"removed": stock_id})
