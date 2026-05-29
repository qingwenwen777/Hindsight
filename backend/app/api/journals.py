"""决策日志 API —— 锁定只读 + 追加复盘。"""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from app.core.money import D, to_db_str
from app.core.response import Meta, ok
from app.database import get_session
from app.models.base import utcnow
from app.models.journal import Journal, Review
from app.models.stock import Stock

router = APIRouter(prefix="/journals", tags=["journals"])


class JournalCreate(BaseModel):
    """独立创建日志（非交易触发，如 WATCH/HOLD 想法记录）。"""

    stock_id: int
    decision_type: str
    thesis_category: str | None = None
    expected_horizon: str | None = None
    target_price: str | None = None
    stop_loss_price: str | None = None
    exit_condition: str | None = None
    confidence: int | None = Field(default=None, ge=1, le=5)
    emotion: str | None = None
    thesis: str = Field(..., min_length=1)
    risks: str | None = None
    tags: list[str] | None = None
    lock: bool = True  # 默认提交即锁定


class ReviewCreate(BaseModel):
    """追加复盘（INSERT，不改 journal 本体）。"""

    review_date: date | None = None
    days_since_decision: int | None = None
    price_at_review: str | None = None
    pnl_pct: str | None = None
    benchmark_pnl_pct: str | None = None
    thesis_held: bool | None = None
    luck_vs_skill: str | None = None
    lessons: str | None = None
    notes: str | None = None


def _serialize_journal(j: Journal) -> dict:
    return {
        "id": j.id,
        "stock_id": j.stock_id,
        "decision_type": j.decision_type,
        "thesis_category": j.thesis_category,
        "expected_horizon": j.expected_horizon,
        "target_price": to_db_str(j.target_price),
        "stop_loss_price": to_db_str(j.stop_loss_price),
        "exit_condition": j.exit_condition,
        "confidence": j.confidence,
        "emotion": j.emotion,
        "thesis": j.thesis,
        "risks": j.risks,
        "tags": j.tags,
        "is_locked": j.is_locked,
        "is_imported": j.is_imported,
        "locked_at": j.locked_at.isoformat() if j.locked_at else None,
        "created_at": j.created_at.isoformat() if j.created_at else None,
    }


def _serialize_review(r: Review) -> dict:
    return {
        "id": r.id,
        "journal_id": r.journal_id,
        "review_date": r.review_date.isoformat(),
        "days_since_decision": r.days_since_decision,
        "price_at_review": to_db_str(r.price_at_review),
        "pnl_pct": to_db_str(r.pnl_pct),
        "benchmark_pnl_pct": to_db_str(r.benchmark_pnl_pct),
        "thesis_held": r.thesis_held,
        "luck_vs_skill": r.luck_vs_skill,
        "lessons": r.lessons,
        "notes": r.notes,
    }


@router.post("", summary="创建决策日志")
def create_journal(payload: JournalCreate, session: Session = Depends(get_session)) -> dict:
    if not session.get(Stock, payload.stock_id):
        raise HTTPException(status_code=404, detail="股票不存在")
    journal = Journal(
        stock_id=payload.stock_id,
        decision_type=payload.decision_type,
        thesis_category=payload.thesis_category,
        expected_horizon=payload.expected_horizon,
        target_price=D(payload.target_price) if payload.target_price else None,
        stop_loss_price=D(payload.stop_loss_price) if payload.stop_loss_price else None,
        exit_condition=payload.exit_condition,
        confidence=payload.confidence,
        emotion=payload.emotion,
        thesis=payload.thesis,
        risks=payload.risks,
        tags=payload.tags,
        is_locked=payload.lock,
        locked_at=utcnow() if payload.lock else None,
    )
    session.add(journal)
    session.commit()
    session.refresh(journal)
    return ok(_serialize_journal(journal))


@router.get("", summary="日志列表")
def list_journals(
    stock_id: int | None = Query(None),
    type: str | None = Query(None),
    emotion: str | None = Query(None),
    session: Session = Depends(get_session),
) -> dict:
    stmt = select(Journal)
    if stock_id:
        stmt = stmt.where(Journal.stock_id == stock_id)
    if type:
        stmt = stmt.where(Journal.decision_type == type.upper())
    if emotion:
        stmt = stmt.where(Journal.emotion == emotion.upper())
    stmt = stmt.order_by(Journal.created_at.desc())
    rows = list(session.exec(stmt).all())
    return ok([_serialize_journal(j) for j in rows], meta=Meta(total=len(rows)))


@router.get("/{journal_id}", summary="日志详情")
def get_journal(journal_id: int, session: Session = Depends(get_session)) -> dict:
    j = session.get(Journal, journal_id)
    if not j:
        raise HTTPException(status_code=404, detail="日志不存在")
    return ok(_serialize_journal(j))


@router.post("/{journal_id}/reviews", summary="追加复盘")
def add_review(
    journal_id: int, payload: ReviewCreate, session: Session = Depends(get_session)
) -> dict:
    """追加复盘（INSERT 到 reviews，不动 journal 本体）。"""
    j = session.get(Journal, journal_id)
    if not j:
        raise HTTPException(status_code=404, detail="日志不存在")
    review = Review(
        journal_id=journal_id,
        review_date=payload.review_date or date.today(),
        days_since_decision=payload.days_since_decision,
        price_at_review=D(payload.price_at_review) if payload.price_at_review else None,
        pnl_pct=D(payload.pnl_pct) if payload.pnl_pct else None,
        benchmark_pnl_pct=D(payload.benchmark_pnl_pct) if payload.benchmark_pnl_pct else None,
        thesis_held=payload.thesis_held,
        luck_vs_skill=payload.luck_vs_skill,
        lessons=payload.lessons,
        notes=payload.notes,
    )
    session.add(review)
    session.commit()
    session.refresh(review)
    return ok(_serialize_review(review))


@router.get("/{journal_id}/reviews", summary="复盘列表")
def list_reviews(journal_id: int, session: Session = Depends(get_session)) -> dict:
    if not session.get(Journal, journal_id):
        raise HTTPException(status_code=404, detail="日志不存在")
    rows = list(
        session.exec(
            select(Review).where(Review.journal_id == journal_id).order_by(Review.review_date)
        ).all()
    )
    return ok([_serialize_review(r) for r in rows], meta=Meta(total=len(rows)))
