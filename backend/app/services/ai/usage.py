"""AI 用量统计（只读，无预算限制）。

仅用于在前端展示"本月 Token 用量 / 对话次数"，不做任何额度拦截。
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlmodel import Session, select

from app.models.ai_insight import AiInsight


def _month_start() -> datetime:
    now = datetime.now(timezone.utc)
    return datetime(now.year, now.month, 1, tzinfo=timezone.utc)


def tokens_this_month(session: Session) -> tuple[int, int, int]:
    """本月 token 用量：(prompt, completion, calls)。"""
    start = _month_start()
    rows = session.exec(
        select(AiInsight.prompt_tokens, AiInsight.completion_tokens).where(
            AiInsight.created_at >= start
        )
    ).all()
    prompt_total = 0
    completion_total = 0
    calls = 0
    for pt, ct in rows:
        calls += 1
        prompt_total += pt or 0
        completion_total += ct or 0
    return prompt_total, completion_total, calls


__all__ = ["tokens_this_month"]
