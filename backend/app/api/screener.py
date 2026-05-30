"""规则筛选 API：规则 CRUD、执行筛选、AI 点评。"""

from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlmodel import Session, select

from app.core.response import Meta, ok
from app.database import engine, get_session
from app.logging_config import get_logger
from app.models.base import utcnow
from app.models.insight import ScreenerRule
from app.services.screener.engine import ALL_FIELDS, OPERATORS, run_screen

router = APIRouter(prefix="/screener", tags=["screener"])
log = get_logger(__name__)


class Condition(BaseModel):
    field: str
    op: str
    value: str | float | int | bool | None = None
    value2: str | float | int | None = None


class RulePayload(BaseModel):
    name: str
    conditions: list[Condition]
    markets: list[str] | None = None


class RunPayload(BaseModel):
    conditions: list[Condition]
    markets: list[str] | None = None


class ReviewPayload(BaseModel):
    conditions: list[Condition] | None = None
    markets: list[str] | None = None
    rule_id: int | None = None
    rule_name: str | None = None
    language: str = "zh"


@router.get("/fields", summary="可用字段与运算符")
def fields() -> dict:
    return ok({"fields": ALL_FIELDS, "operators": sorted(OPERATORS)})


@router.get("/rules", summary="筛选规则列表")
def list_rules(session: Session = Depends(get_session)) -> dict:
    rows = list(session.exec(select(ScreenerRule).order_by(ScreenerRule.updated_at.desc())).all())
    data = [
        {
            "id": r.id,
            "name": r.name,
            "conditions": r.conditions,
            "markets": r.markets,
            "updated_at": r.updated_at.isoformat() if r.updated_at else None,
        }
        for r in rows
    ]
    return ok(data, meta=Meta(total=len(data)))


@router.post("/rules", summary="创建规则")
def create_rule(payload: RulePayload, session: Session = Depends(get_session)) -> dict:
    rule = ScreenerRule(
        name=payload.name,
        conditions=[c.model_dump() for c in payload.conditions],
        markets=payload.markets,
    )
    session.add(rule)
    session.commit()
    session.refresh(rule)
    return ok({"id": rule.id})


@router.put("/rules/{rule_id}", summary="更新规则")
def update_rule(rule_id: int, payload: RulePayload, session: Session = Depends(get_session)) -> dict:
    rule = session.get(ScreenerRule, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="规则不存在")
    rule.name = payload.name
    rule.conditions = [c.model_dump() for c in payload.conditions]
    rule.markets = payload.markets
    rule.updated_at = utcnow()
    session.add(rule)
    session.commit()
    return ok({"id": rule_id})


@router.delete("/rules/{rule_id}", summary="删除规则")
def delete_rule(rule_id: int, session: Session = Depends(get_session)) -> dict:
    rule = session.get(ScreenerRule, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="规则不存在")
    session.delete(rule)
    session.commit()
    return ok({"removed": rule_id})


@router.post("/run", summary="执行筛选")
def run(payload: RunPayload, session: Session = Depends(get_session)) -> dict:
    conds = [c.model_dump() for c in payload.conditions]
    hits = run_screen(session, conds, payload.markets)
    data = [
        {
            "stock_id": h.stock_id,
            "symbol": h.symbol,
            "name": h.name,
            "market": h.market,
            "matched": h.matched,
            "missing": h.missing,
        }
        for h in hits
    ]
    return ok(data, meta=Meta(total=len(data)))


def _review_task(conditions: list[dict], markets: list[str] | None, rule_name: str | None, language: str) -> None:
    try:
        with Session(engine) as session:
            hits = run_screen(session, conditions, markets)
            from app.services.insights.screener_review import review_hits

            review_hits(session, hits, language=language, rule_name=rule_name)
    except Exception as e:  # noqa: BLE001
        log.warning("screener.review_failed", error=str(e))


@router.post("/review", summary="对筛选结果请求 AI 点评")
def review(
    payload: ReviewPayload,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session),
) -> dict:
    # 解析条件：优先 rule_id
    conditions: list[dict]
    markets = payload.markets
    rule_name = payload.rule_name
    if payload.rule_id is not None:
        rule = session.get(ScreenerRule, payload.rule_id)
        if not rule:
            raise HTTPException(status_code=404, detail="规则不存在")
        conditions = rule.conditions
        markets = rule.markets
        rule_name = rule.name
    elif payload.conditions is not None:
        conditions = [c.model_dump() for c in payload.conditions]
    else:
        raise HTTPException(status_code=422, detail="需提供 conditions 或 rule_id")

    background_tasks.add_task(_review_task, conditions, markets, rule_name, payload.language)
    return ok({"status": "reviewing"})
