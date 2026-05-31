"""AI 分析 API：analyze / insights / usage。"""

from __future__ import annotations

import json
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlmodel import Session, select

from app.config import settings
from app.core.money import to_db_str
from app.core.response import Meta, ok
from app.database import get_session
from app.models.ai_insight import AiInsight
from app.services.ai import client as ai_client
from app.services.ai import context_builder, prompts

router = APIRouter(prefix="/ai", tags=["ai"])


class AnalyzeRequest(BaseModel):
    type: str  # TRADE_REVIEW / DEVILS_ADVOCATE / FAILURE_PATTERN
    target_id: int | None = None
    start: date | None = None
    end: date | None = None


class ChatContextRef(BaseModel):
    """对话引用的上下文项。"""

    type: str  # HOLDING / TRANSACTION / JOURNAL
    id: int


class ChatRequest(BaseModel):
    message: str
    context_refs: list[ChatContextRef] = []
    provider_id: int | None = None
    model: str | None = None


@router.post("/analyze", summary="AI 分析")
def analyze(payload: AnalyzeRequest, session: Session = Depends(get_session)) -> dict:
    """对交易/日志/组合执行 AI 分析（带缓存与预算）。"""
    ptype = payload.type.upper()

    try:
        if ptype == "TRADE_REVIEW":
            if not payload.target_id:
                raise HTTPException(status_code=422, detail="缺少 target_id")
            context = context_builder.build_trade_review_context(session, payload.target_id)
            user_content = prompts.render_trade_review(context)
            target_type, target_id = "TRANSACTION", payload.target_id
        elif ptype == "DEVILS_ADVOCATE":
            if not payload.target_id:
                raise HTTPException(status_code=422, detail="缺少 target_id")
            decision = context_builder.build_devils_advocate_context(session, payload.target_id)
            user_content = prompts.render_devils_advocate(decision)
            target_type, target_id = "JOURNAL", payload.target_id
        elif ptype in ("FAILURE_PATTERN", "QUARTERLY_REVIEW"):
            end = payload.end or date.today()
            start = payload.start or (end - timedelta(days=90))
            summary = context_builder.build_failure_pattern_context(session, start, end)
            user_content = prompts.render_failure_pattern(summary)
            target_type, target_id = "PORTFOLIO", None
        else:
            raise HTTPException(status_code=422, detail=f"未知分析类型：{ptype}")
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

    result = ai_client.analyze(
        session,
        prompt_type=ptype,
        system_prompt=prompts.SYSTEM_BASE,
        user_content=user_content,
        target_type=target_type,
        target_id=target_id,
        max_tokens=settings.ai_analysis_max_tokens,
    )

    return ok(
        {
            "type": ptype,
            "response": result.response,
            "model": result.model,
            "cached": result.cached,
            "degraded": result.degraded,
            "cost_jpy": to_db_str(result.cost_jpy),
            "prompt_tokens": result.prompt_tokens,
            "completion_tokens": result.completion_tokens,
        }
    )


@router.get("/insights", summary="AI 洞察列表")
def list_insights(
    target_type: str | None = Query(None),
    target_id: int | None = Query(None),
    limit: int = Query(50, le=200),
    session: Session = Depends(get_session),
) -> dict:
    stmt = select(AiInsight)
    if target_type:
        stmt = stmt.where(AiInsight.target_type == target_type.upper())
    if target_id is not None:
        stmt = stmt.where(AiInsight.target_id == target_id)
    stmt = stmt.order_by(AiInsight.created_at.desc()).limit(limit)
    rows = list(session.exec(stmt).all())
    data = [
        {
            "id": r.id,
            "target_type": r.target_type,
            "target_id": r.target_id,
            "prompt_type": r.prompt_type,
            "model": r.model,
            "cost_jpy": to_db_str(r.cost_jpy),
            "response": r.response,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]
    return ok(data, meta=Meta(total=len(data)))


@router.get("/usage", summary="AI 用量（本月 Token / 对话次数）")
def get_usage(session: Session = Depends(get_session)) -> dict:
    """返回本月 Token 用量与对话次数（仅统计展示，无预算限制）。"""
    from app.services.ai.usage import tokens_this_month

    prompt_tokens, completion_tokens, calls = tokens_this_month(session)
    return ok(
        {
            "available": ai_client.is_available(session),
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
            "calls": calls,
        }
    )


@router.post("/chat", summary="AI 对话")
def chat(payload: ChatRequest, session: Session = Depends(get_session)) -> dict:
    """基于选中的持仓/交易/日志上下文进行对话。"""
    refs = [(r.type, r.id) for r in payload.context_refs]
    context = context_builder.build_chat_context(session, refs)
    user_content = (
        f"## 可引用的数据（数字由系统精确计算）\n{context}\n\n"
        f"## 用户问题\n{payload.message}"
    )
    result = ai_client.analyze(
        session,
        prompt_type="CHAT",
        system_prompt=prompts.SYSTEM_BASE,
        user_content=user_content,
        target_type="PORTFOLIO",
        target_id=None,
        max_tokens=settings.ai_chat_max_tokens,
        provider_id=payload.provider_id,
        force_model=payload.model,
    )

    return ok(
        {
            "response": result.response,
            "model": result.model,
            "cached": result.cached,
            "degraded": result.degraded,
            "cost_jpy": to_db_str(result.cost_jpy),
            "prompt_tokens": result.prompt_tokens,
            "completion_tokens": result.completion_tokens,
        }
    )


@router.post("/chat/stream", summary="AI 对话（流式 SSE）")
def chat_stream(payload: ChatRequest, session: Session = Depends(get_session)):  # noqa: ANN201
    """与 /chat 相同，但以 Server-Sent Events 流式逐段返回 AI 输出。

    事件格式（每条 `data: <json>\\n\\n`）：
      {"type":"meta","model":...,"cached":...,"degraded":...}
      {"type":"delta","text":...}
      {"type":"done","cost_jpy":...,"prompt_tokens":...,"completion_tokens":...}
      {"type":"error","message":...}
    """
    refs = [(r.type, r.id) for r in payload.context_refs]
    context = context_builder.build_chat_context(session, refs)
    user_content = (
        f"## 可引用的数据（数字由系统精确计算）\n{context}\n\n"
        f"## 用户问题\n{payload.message}"
    )

    def event_stream():
        def sse(obj: dict) -> str:
            return f"data: {json.dumps(obj, ensure_ascii=False)}\n\n"

        try:
            events = ai_client.analyze_stream(
                session,
                prompt_type="CHAT",
                system_prompt=prompts.SYSTEM_BASE,
                user_content=user_content,
                target_type="PORTFOLIO",
                target_id=None,
                max_tokens=settings.ai_chat_max_tokens,
                provider_id=payload.provider_id,
                force_model=payload.model,
            )
            for ev in events:
                if ev.type == "meta":
                    yield sse(
                        {
                            "type": "meta",
                            "model": ev.model,
                            "cached": ev.cached,
                            "degraded": ev.degraded,
                        }
                    )
                elif ev.type == "delta":
                    yield sse({"type": "delta", "text": ev.text})
                elif ev.type == "done":
                    yield sse(
                        {
                            "type": "done",
                            "model": ev.model,
                            "cached": ev.cached,
                            "degraded": ev.degraded,
                            "cost_jpy": to_db_str(ev.cost_jpy),
                            "prompt_tokens": ev.prompt_tokens,
                            "completion_tokens": ev.completion_tokens,
                        }
                    )
                elif ev.type == "error":
                    yield sse({"type": "error", "message": ev.message})
        except Exception as e:  # noqa: BLE001 — 任何异常都回传给前端
            yield sse({"type": "error", "message": str(e)})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # 禁用 nginx 缓冲，保证逐段下发
        },
    )


@router.post("/quarterly-review", summary="AI 季度模式分析")
def quarterly_review(
    year: int = Query(...),
    quarter: int = Query(..., ge=1, le=4),
    session: Session = Depends(get_session),
) -> dict:
    """对某季度的亏损交易做失败模式识别，返回 AI 模式分析 + 支撑交易列表。"""
    from datetime import date

    from app.services.analysis.reports import build_failure_library

    start_month = (quarter - 1) * 3 + 1
    start = date(year, start_month, 1)
    end = date(year + 1, 1, 1) if start_month + 3 > 12 else date(year, start_month + 3, 1)

    summary = context_builder.build_failure_pattern_context(session, start, end)
    user_content = prompts.render_failure_pattern(summary)

    result = ai_client.analyze(
        session,
        prompt_type="QUARTERLY_REVIEW",
        system_prompt=prompts.SYSTEM_BASE,
        user_content=user_content,
        target_type="PORTFOLIO",
        target_id=None,
        max_tokens=settings.ai_analysis_max_tokens,
    )

    # 支撑交易（该季度内的失败案例）
    all_failures = build_failure_library(session)
    supporting = [
        {
            "transaction_id": c.transaction_id,
            "symbol": c.symbol,
            "trade_date": c.trade_date,
            "return_30d_pct": to_db_str(c.return_30d),
        }
        for c in all_failures
        if start.isoformat() <= c.trade_date < end.isoformat()
    ]

    return ok(
        {
            "period": f"{year}Q{quarter}",
            "response": result.response,
            "model": result.model,
            "cached": result.cached,
            "degraded": result.degraded,
            "cost_jpy": to_db_str(result.cost_jpy),
            "supporting_transactions": supporting,
        }
    )
