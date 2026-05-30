"""Anthropic 客户端封装 —— 缓存 + 预算 + 优雅降级。

无 ANTHROPIC_API_KEY 时优雅降级（返回降级提示，不崩溃）。
缓存：input_hash = sha256(prompt_type + context)，7 天内命中直接返回，不再扣费。
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal

from sqlmodel import Session, select

from app.config import settings
from app.core.money import D
from app.logging_config import get_logger
from app.models.ai_insight import AiInsight
from app.models.base import utcnow
from app.services.ai.budget import BudgetExceeded, BudgetGuard
from app.services.ai.models import estimate_cost_jpy, model_for

log = get_logger(__name__)

CACHE_TTL_DAYS = 7

# AI 输出统一附带的声明
DISCLAIMER = "\n\n---\n*AI 仅供参考，不构成投资建议，不预测股价、不提供买卖信号。*"


class AiUnavailable(Exception):
    """AI 不可用（无 key / SDK 未装）。"""


@dataclass
class AiResult:
    response: str
    model: str
    cached: bool
    cost_jpy: Decimal
    prompt_tokens: int
    completion_tokens: int
    degraded: bool = False


def compute_hash(prompt_type: str, context: str) -> str:
    """缓存键。"""
    return hashlib.sha256(f"{prompt_type}\n{context}".encode()).hexdigest()


def _get_cached(
    session: Session, prompt_type: str, input_hash: str
) -> AiInsight | None:
    cutoff = utcnow() - timedelta(days=CACHE_TTL_DAYS)
    stmt = (
        select(AiInsight)
        .where(
            AiInsight.prompt_type == prompt_type,
            AiInsight.input_hash == input_hash,
            AiInsight.created_at >= cutoff,
        )
        .order_by(AiInsight.created_at.desc())
        .limit(1)
    )
    return session.exec(stmt).first()


def is_available() -> bool:
    """AI 是否可用（有 key 且 SDK 可导入）。"""
    if not settings.anthropic_api_key:
        return False
    try:
        import anthropic  # noqa: F401, PLC0415

        return True
    except ImportError:
        return False


def analyze(
    session: Session,
    *,
    prompt_type: str,
    system_prompt: str,
    user_content: str,
    target_type: str,
    target_id: int | None,
    max_tokens: int = 1024,
    force_model: str | None = None,
) -> AiResult:
    """执行一次 AI 分析（带缓存与预算）。

    流程：算 hash → 查缓存(命中直接返回，不扣费) → 预算检查 → 调用 → 写缓存。
    无 key 优雅降级。
    """
    input_hash = compute_hash(prompt_type, user_content)

    # 1. 缓存命中
    cached = _get_cached(session, prompt_type, input_hash)
    if cached is not None:
        log.info("ai.cache_hit", prompt_type=prompt_type, hash=input_hash[:8])
        return AiResult(
            response=cached.response,
            model=cached.model,
            cached=True,
            cost_jpy=D(cached.cost_jpy) if cached.cost_jpy else Decimal("0"),
            prompt_tokens=cached.prompt_tokens or 0,
            completion_tokens=cached.completion_tokens or 0,
        )

    model = force_model or settings.ai_model or model_for(prompt_type)

    # 2. 无 key → 优雅降级
    if not is_available():
        msg = (
            "（AI 未配置：缺少 API Key，已跳过实际分析。"
            "请在 backend/.env 配置 ANTHROPIC_API_KEY 后重试。）" + DISCLAIMER
        )
        return AiResult(
            response=msg,
            model=model,
            cached=False,
            cost_jpy=Decimal("0"),
            prompt_tokens=0,
            completion_tokens=0,
            degraded=True,
        )

    # 3. 预算检查（用粗略预估）
    guard = BudgetGuard(session)
    est_prompt = len(user_content) // 3 + len(system_prompt) // 3
    est_cost = estimate_cost_jpy(model, est_prompt, max_tokens)
    guard.ensure(est_cost)  # 超限抛 BudgetExceeded

    # 4. 真正调用（支持自定义 base_url，如 DeepSeek 的 Anthropic 兼容端点）
    import anthropic  # noqa: PLC0415

    client_kwargs: dict = {"api_key": settings.anthropic_api_key}
    if settings.ai_base_url:
        client_kwargs["base_url"] = settings.ai_base_url
    client = anthropic.Anthropic(**client_kwargs)
    msg = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system_prompt,
        messages=[{"role": "user", "content": user_content}],
    )
    text = "".join(b.text for b in msg.content if getattr(b, "type", None) == "text")
    text += DISCLAIMER

    prompt_tokens = msg.usage.input_tokens
    completion_tokens = msg.usage.output_tokens
    cost = estimate_cost_jpy(model, prompt_tokens, completion_tokens)

    # 5. 写缓存
    insight = AiInsight(
        target_type=target_type,
        target_id=target_id,
        prompt_type=prompt_type,
        input_hash=input_hash,
        model=model,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        cost_jpy=cost,
        response=text,
    )
    session.add(insight)
    session.commit()

    if guard.is_close():
        log.warning("ai.budget_close", ratio=round(guard.usage_ratio(), 2))

    return AiResult(
        response=text,
        model=model,
        cached=False,
        cost_jpy=cost,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
    )


@dataclass
class StreamEvent:
    """流式事件。

    type:
      - "meta"  : 开始前的元信息（model / cached）
      - "delta" : 一段新生成的文本
      - "done"  : 结束，附带最终统计（cost/tokens）
      - "error" : 出错
    """

    type: str
    text: str = ""
    model: str = ""
    cached: bool = False
    degraded: bool = False
    cost_jpy: Decimal = Decimal("0")
    prompt_tokens: int = 0
    completion_tokens: int = 0
    message: str = ""


def analyze_stream(
    session: Session,
    *,
    prompt_type: str,
    system_prompt: str,
    user_content: str,
    target_type: str,
    target_id: int | None,
    max_tokens: int = 1024,
    force_model: str | None = None,
    history: list[dict] | None = None,
) -> Iterator[StreamEvent]:
    """流式执行一次 AI 分析（带缓存与预算），逐段产出文本。

    流程与 analyze 一致：算 hash → 查缓存(命中直接整段返回) → 预算检查 →
    流式调用并累积 → 写缓存。无 key 优雅降级。

    history: 多轮对话历史 [{"role": "user"|"assistant", "content": str}]，
    会拼到本轮 user 消息之前一并发送给模型；同时纳入缓存键，确保不同
    对话上下文不会命中彼此的缓存。

    注意：BudgetExceeded 会在迭代开始时抛出，调用方需在进入流之前处理。
    """
    history = history or []
    # 历史纳入缓存键：不同对话上下文的相同问句不应命中同一缓存
    hash_basis = user_content
    if history:
        hist_repr = "\n".join(f"{m.get('role')}:{m.get('content')}" for m in history)
        hash_basis = f"{hist_repr}\n---\n{user_content}"
    input_hash = compute_hash(prompt_type, hash_basis)

    # 1. 缓存命中：直接整段吐出（仍走流式协议，前端体验一致）
    cached = _get_cached(session, prompt_type, input_hash)
    if cached is not None:
        log.info("ai.cache_hit", prompt_type=prompt_type, hash=input_hash[:8])
        yield StreamEvent(type="meta", model=cached.model, cached=True)
        yield StreamEvent(type="delta", text=cached.response)
        yield StreamEvent(
            type="done",
            model=cached.model,
            cached=True,
            cost_jpy=D(cached.cost_jpy) if cached.cost_jpy else Decimal("0"),
            prompt_tokens=cached.prompt_tokens or 0,
            completion_tokens=cached.completion_tokens or 0,
        )
        return

    model = force_model or settings.ai_model or model_for(prompt_type)

    # 2. 无 key → 优雅降级
    if not is_available():
        msg = (
            "（AI 未配置：缺少 API Key，已跳过实际分析。"
            "请在 backend/.env 配置 ANTHROPIC_API_KEY 后重试。）" + DISCLAIMER
        )
        yield StreamEvent(type="meta", model=model, degraded=True)
        yield StreamEvent(type="delta", text=msg)
        yield StreamEvent(type="done", model=model, degraded=True)
        return

    # 3. 预算检查（用粗略预估）
    guard = BudgetGuard(session)
    hist_len = sum(len(m.get("content", "")) for m in history)
    est_prompt = (len(user_content) + hist_len) // 3 + len(system_prompt) // 3
    est_cost = estimate_cost_jpy(model, est_prompt, max_tokens)
    guard.ensure(est_cost)  # 超限抛 BudgetExceeded

    # 4. 流式调用
    import anthropic  # noqa: PLC0415

    client_kwargs: dict = {"api_key": settings.anthropic_api_key}
    if settings.ai_base_url:
        client_kwargs["base_url"] = settings.ai_base_url
    client = anthropic.Anthropic(**client_kwargs)

    yield StreamEvent(type="meta", model=model, cached=False)

    # 拼接多轮历史 + 本轮问句
    messages: list[dict] = [
        {"role": m["role"], "content": m["content"]}
        for m in history
        if m.get("role") in ("user", "assistant") and m.get("content")
    ]
    messages.append({"role": "user", "content": user_content})

    parts: list[str] = []
    prompt_tokens = 0
    completion_tokens = 0
    try:
        with client.messages.stream(
            model=model,
            max_tokens=max_tokens,
            system=system_prompt,
            messages=messages,
        ) as stream:
            for text in stream.text_stream:
                if text:
                    parts.append(text)
                    yield StreamEvent(type="delta", text=text)
            final = stream.get_final_message()
        prompt_tokens = final.usage.input_tokens
        completion_tokens = final.usage.output_tokens
    except Exception as e:  # noqa: BLE001 — 网络/SDK 异常都要回传给前端
        log.error("ai.stream_error", error=str(e), prompt_type=prompt_type)
        yield StreamEvent(type="error", model=model, message=str(e))
        return

    # 末尾追加免责声明
    yield StreamEvent(type="delta", text=DISCLAIMER)
    text = "".join(parts) + DISCLAIMER

    cost = estimate_cost_jpy(model, prompt_tokens, completion_tokens)

    # 5. 写缓存
    insight = AiInsight(
        target_type=target_type,
        target_id=target_id,
        prompt_type=prompt_type,
        input_hash=input_hash,
        model=model,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        cost_jpy=cost,
        response=text,
    )
    session.add(insight)
    session.commit()

    if guard.is_close():
        log.warning("ai.budget_close", ratio=round(guard.usage_ratio(), 2))

    yield StreamEvent(
        type="done",
        model=model,
        cached=False,
        cost_jpy=cost,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
    )
