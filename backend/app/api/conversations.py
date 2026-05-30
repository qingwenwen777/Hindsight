"""AI 对话持久化 API：会话 CRUD + 会话内流式对话。

- 会话列表 / 新建 / 重命名 / 删除
- 单会话历史消息读取
- 在某会话内流式提问（SSE），自动持久化用户消息与 AI 回复，并维护多轮上下文
"""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlmodel import Session, select

from app.core.money import D, to_db_str
from app.core.response import Meta, ok
from app.database import engine, get_session
from app.models.base import utcnow
from app.models.conversation import Conversation, ConversationMessage
from app.services.ai import client as ai_client
from app.services.ai import context_builder, prompts
from app.services.ai.budget import BudgetExceeded

router = APIRouter(prefix="/conversations", tags=["conversations"])

# 发给模型的多轮历史最多带几条（控制 token 成本）
MAX_HISTORY_MESSAGES = 12


class ContextRef(BaseModel):
    type: str  # HOLDING / TRANSACTION / JOURNAL
    id: int


class CreateConversationRequest(BaseModel):
    title: str | None = None


class RenameConversationRequest(BaseModel):
    title: str


class ConversationChatRequest(BaseModel):
    message: str
    context_refs: list[ContextRef] = []
    provider_id: int | None = None
    model: str | None = None


def _conv_brief(c: Conversation, message_count: int | None = None) -> dict:
    out = {
        "id": c.id,
        "title": c.title,
        "created_at": c.created_at.isoformat() if c.created_at else None,
        "updated_at": c.updated_at.isoformat() if c.updated_at else None,
    }
    if message_count is not None:
        out["message_count"] = message_count
    return out


def _msg_dict(m: ConversationMessage) -> dict:
    return {
        "id": m.id,
        "conversation_id": m.conversation_id,
        "role": m.role,
        "content": m.content,
        "model": m.model,
        "prompt_tokens": m.prompt_tokens,
        "completion_tokens": m.completion_tokens,
        "cost_jpy": to_db_str(m.cost_jpy) if m.cost_jpy is not None else None,
        "cached": m.cached,
        "context_refs": m.context_refs,
        "created_at": m.created_at.isoformat() if m.created_at else None,
    }


@router.get("", summary="会话列表")
def list_conversations(
    limit: int = Query(100, le=500),
    session: Session = Depends(get_session),
) -> dict:
    rows = list(
        session.exec(
            select(Conversation).order_by(Conversation.updated_at.desc()).limit(limit)
        ).all()
    )
    data = []
    for c in rows:
        count = len(
            list(
                session.exec(
                    select(ConversationMessage.id).where(
                        ConversationMessage.conversation_id == c.id
                    )
                ).all()
            )
        )
        data.append(_conv_brief(c, message_count=count))
    return ok(data, meta=Meta(total=len(data)))


@router.post("", summary="新建会话")
def create_conversation(
    payload: CreateConversationRequest, session: Session = Depends(get_session)
) -> dict:
    conv = Conversation(title=(payload.title or "新对话").strip()[:120] or "新对话")
    session.add(conv)
    session.commit()
    session.refresh(conv)
    return ok(_conv_brief(conv, message_count=0))


@router.get("/{conv_id}", summary="会话详情（含消息）")
def get_conversation(conv_id: int, session: Session = Depends(get_session)) -> dict:
    conv = session.get(Conversation, conv_id)
    if not conv:
        raise HTTPException(status_code=404, detail="会话不存在")
    msgs = list(
        session.exec(
            select(ConversationMessage)
            .where(ConversationMessage.conversation_id == conv_id)
            .order_by(ConversationMessage.created_at, ConversationMessage.id)
        ).all()
    )
    return ok({**_conv_brief(conv, message_count=len(msgs)), "messages": [_msg_dict(m) for m in msgs]})


@router.patch("/{conv_id}", summary="重命名会话")
def rename_conversation(
    conv_id: int, payload: RenameConversationRequest, session: Session = Depends(get_session)
) -> dict:
    conv = session.get(Conversation, conv_id)
    if not conv:
        raise HTTPException(status_code=404, detail="会话不存在")
    title = payload.title.strip()[:120]
    if not title:
        raise HTTPException(status_code=422, detail="标题不能为空")
    conv.title = title
    conv.updated_at = utcnow()
    session.add(conv)
    session.commit()
    return ok(_conv_brief(conv))


@router.delete("/{conv_id}", summary="删除会话")
def delete_conversation(conv_id: int, session: Session = Depends(get_session)) -> dict:
    conv = session.get(Conversation, conv_id)
    if not conv:
        raise HTTPException(status_code=404, detail="会话不存在")
    # 先批量删消息并 flush，确保子记录先于父记录删除（无 ORM 关系，需手动保证顺序）
    msgs = session.exec(
        select(ConversationMessage).where(ConversationMessage.conversation_id == conv_id)
    ).all()
    for m in msgs:
        session.delete(m)
    session.flush()
    session.delete(conv)
    session.commit()
    return ok({"id": conv_id, "deleted": True})


def _derive_title(message: str) -> str:
    """用首条用户消息生成简短标题。"""
    text = " ".join(message.split())
    return text[:24] if text else "新对话"


@router.post("/{conv_id}/chat/stream", summary="会话内流式对话（SSE）")
def conversation_chat_stream(
    conv_id: int,
    payload: ConversationChatRequest,
    session: Session = Depends(get_session),
):  # noqa: ANN201
    """在指定会话内提问，流式返回，并持久化用户消息 + AI 回复，维护多轮上下文。"""
    conv = session.get(Conversation, conv_id)
    if not conv:
        raise HTTPException(status_code=404, detail="会话不存在")

    refs = [(r.type, r.id) for r in payload.context_refs]
    context = context_builder.build_chat_context(session, refs)
    user_content = (
        f"## 可引用的数据（数字由系统精确计算）\n{context}\n\n"
        f"## 用户问题\n{payload.message}"
    )

    # 读取既有历史（截断到最近 N 条）作为多轮上下文
    prior = list(
        session.exec(
            select(ConversationMessage)
            .where(ConversationMessage.conversation_id == conv_id)
            .order_by(ConversationMessage.created_at, ConversationMessage.id)
        ).all()
    )
    history = [{"role": m.role, "content": m.content} for m in prior][-MAX_HISTORY_MESSAGES:]
    is_first = len(prior) == 0

    # 立即持久化用户消息
    user_msg = ConversationMessage(
        conversation_id=conv_id,
        role="user",
        content=payload.message,
        context_refs=[{"type": r.type, "id": r.id} for r in payload.context_refs] or None,
    )
    session.add(user_msg)
    if is_first:
        conv.title = _derive_title(payload.message)
    conv.updated_at = utcnow()
    session.add(conv)
    session.commit()

    def event_stream():
        def sse(obj: dict) -> str:
            return f"data: {json.dumps(obj, ensure_ascii=False)}\n\n"

        collected: list[str] = []
        meta = {"model": "", "cached": False, "cost_jpy": None, "prompt_tokens": 0, "completion_tokens": 0}
        had_error = False

        if is_first:
            yield sse({"type": "title", "title": conv.title})

        # 用独立 session 跑流，避免与请求 session 的事务交织
        stream_session = Session(engine)
        try:
            events = ai_client.analyze_stream(
                stream_session,
                prompt_type="CHAT",
                system_prompt=prompts.SYSTEM_BASE,
                user_content=user_content,
                target_type="PORTFOLIO",
                target_id=None,
                max_tokens=1500,
                history=history,
                provider_id=payload.provider_id,
                force_model=payload.model,
            )
            for ev in events:
                if ev.type == "meta":
                    meta["model"] = ev.model
                    meta["cached"] = ev.cached
                    yield sse(
                        {
                            "type": "meta",
                            "model": ev.model,
                            "cached": ev.cached,
                            "degraded": ev.degraded,
                        }
                    )
                elif ev.type == "delta":
                    collected.append(ev.text)
                    yield sse({"type": "delta", "text": ev.text})
                elif ev.type == "done":
                    meta["model"] = ev.model or meta["model"]
                    meta["cached"] = ev.cached
                    meta["cost_jpy"] = to_db_str(ev.cost_jpy)
                    meta["prompt_tokens"] = ev.prompt_tokens
                    meta["completion_tokens"] = ev.completion_tokens
                elif ev.type == "error":
                    had_error = True
                    yield sse({"type": "error", "message": ev.message})
        except BudgetExceeded as e:
            had_error = True
            yield sse({"type": "error", "message": str(e)})
        finally:
            stream_session.close()

        full_text = "".join(collected)

        # 持久化 AI 回复（即使出错也存已生成的部分，便于回看）
        if full_text or not had_error:
            persist_session = Session(engine)
            try:
                ai_msg = ConversationMessage(
                    conversation_id=conv_id,
                    role="assistant",
                    content=full_text,
                    model=meta["model"] or None,
                    prompt_tokens=meta["prompt_tokens"],
                    completion_tokens=meta["completion_tokens"],
                    cost_jpy=D(meta["cost_jpy"]) if meta["cost_jpy"] else None,
                    cached=meta["cached"],
                )
                persist_session.add(ai_msg)
                conv_row = persist_session.get(Conversation, conv_id)
                if conv_row:
                    conv_row.updated_at = utcnow()
                    persist_session.add(conv_row)
                persist_session.commit()
                persist_session.refresh(ai_msg)
                msg_id = ai_msg.id
            finally:
                persist_session.close()
        else:
            msg_id = None

        yield sse(
            {
                "type": "done",
                "message_id": msg_id,
                "model": meta["model"],
                "cached": meta["cached"],
                "cost_jpy": meta["cost_jpy"],
                "prompt_tokens": meta["prompt_tokens"],
                "completion_tokens": meta["completion_tokens"],
            }
        )

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
