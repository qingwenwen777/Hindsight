"""AI 客户端封装 —— 多服务商 + 缓存 + 预算 + 优雅降级。

支持用户在 ai_providers 表里配置多个服务商（OpenAI / Anthropic 协议），
对话/分析时按"显式指定 > 全局默认 > env 兜底"解析使用哪个服务商与模型。

缓存：input_hash = sha256(prompt_type + model + context)，7 天内命中直接返回。
预算：仅对内置已知定价的模型计成本与预算限制；自定义服务商模型不计成本、不限预算。
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal

from sqlmodel import Session, select

from app.core.money import D
from app.logging_config import get_logger
from app.models.ai_insight import AiInsight
from app.models.base import utcnow
from app.services.ai import providers
from app.services.ai.budget import BudgetExceeded, BudgetGuard
from app.services.ai.models import MODEL_PRICING_USD, estimate_cost_jpy

log = get_logger(__name__)

CACHE_TTL_DAYS = 7

# AI 输出统一附带的声明
DISCLAIMER = "\n\n---\n*AI 仅供参考，不构成投资建议，不预测股价、不提供买卖信号。*"


class AiUnavailable(Exception):
    """AI 不可用（无服务商配置）。"""


@dataclass
class AiResult:
    response: str
    model: str
    cached: bool
    cost_jpy: Decimal
    prompt_tokens: int
    completion_tokens: int
    degraded: bool = False
    provider_id: int | None = None


def compute_hash(prompt_type: str, model: str, context: str) -> str:
    """缓存键：含模型，确保不同模型不串味。"""
    return hashlib.sha256(f"{prompt_type}\n{model}\n{context}".encode()).hexdigest()


def _get_cached(session: Session, prompt_type: str, input_hash: str) -> AiInsight | None:
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


def is_available(session: Session | None = None) -> bool:
    """AI 是否可用（存在 enabled 的服务商，或 env 兜底）。"""
    if session is not None:
        return providers.has_any_provider(session)
    # 无 session 时只能判断 env 兜底
    from app.config import settings

    return bool(settings.anthropic_api_key)


def _is_priced(model: str) -> bool:
    """该模型是否在内置定价表内（决定是否计成本/限预算）。"""
    return model in MODEL_PRICING_USD


def _degraded_result(model: str) -> AiResult:
    msg = (
        "（AI 未配置：还没有可用的 AI 服务商。"
        "请到「AI 洞察 → AI 配置」添加一个服务商并填入 API Key 后重试。）" + DISCLAIMER
    )
    return AiResult(
        response=msg, model=model, cached=False, cost_jpy=Decimal("0"),
        prompt_tokens=0, completion_tokens=0, degraded=True,
    )


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
    provider_id: int | None = None,
) -> AiResult:
    """执行一次 AI 分析（带缓存与预算）。

    流程：解析服务商 → 算 hash → 查缓存 → 预算检查（仅计价模型）→ 调用 → 写缓存。
    """
    rp = providers.resolve(session, provider_id=provider_id, model=force_model)

    # 无服务商 → 优雅降级
    if rp is None:
        return _degraded_result(force_model or "unknown")

    model = rp.model
    input_hash = compute_hash(prompt_type, model, user_content)

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
            provider_id=rp.provider_id,
        )

    priced = _is_priced(model)

    # 2. 预算检查（仅对内置计价模型）
    guard = BudgetGuard(session)
    if priced:
        est_prompt = len(user_content) // 3 + len(system_prompt) // 3
        est_cost = estimate_cost_jpy(model, est_prompt, max_tokens)
        guard.ensure(est_cost)  # 超限抛 BudgetExceeded

    # 3. 调用
    result = providers.call(
        rp,
        system_prompt=system_prompt,
        messages=[{"role": "user", "content": user_content}],
        max_tokens=max_tokens,
    )
    text = result.text + DISCLAIMER

    prompt_tokens = result.prompt_tokens
    completion_tokens = result.completion_tokens
    cost = estimate_cost_jpy(model, prompt_tokens, completion_tokens) if priced else Decimal("0")

    # 4. 写缓存
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

    if priced and guard.is_close():
        log.warning("ai.budget_close", ratio=round(guard.usage_ratio(), 2))

    return AiResult(
        response=text,
        model=model,
        cached=False,
        cost_jpy=cost,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        provider_id=rp.provider_id,
    )


@dataclass
class StreamEvent:
    """流式事件。type: meta / delta / done / error。"""

    type: str
    text: str = ""
    model: str = ""
    cached: bool = False
    degraded: bool = False
    cost_jpy: Decimal = Decimal("0")
    prompt_tokens: int = 0
    completion_tokens: int = 0
    message: str = ""
    provider_id: int | None = None


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
    provider_id: int | None = None,
    history: list[dict] | None = None,
) -> Iterator[StreamEvent]:
    """流式执行一次 AI 分析（带缓存与预算），逐段产出文本。

    history: 多轮对话历史 [{"role","content"}]，拼到本轮 user 消息前；纳入缓存键。
    """
    history = history or []

    rp = providers.resolve(session, provider_id=provider_id, model=force_model)
    if rp is None:
        d = _degraded_result(force_model or "unknown")
        yield StreamEvent(type="meta", model=d.model, degraded=True)
        yield StreamEvent(type="delta", text=d.response)
        yield StreamEvent(type="done", model=d.model, degraded=True)
        return

    model = rp.model

    # 历史纳入缓存键
    hash_basis = user_content
    if history:
        hist_repr = "\n".join(f"{m.get('role')}:{m.get('content')}" for m in history)
        hash_basis = f"{hist_repr}\n---\n{user_content}"
    input_hash = compute_hash(prompt_type, model, hash_basis)

    # 1. 缓存命中：整段回放
    cached = _get_cached(session, prompt_type, input_hash)
    if cached is not None:
        log.info("ai.cache_hit", prompt_type=prompt_type, hash=input_hash[:8])
        yield StreamEvent(type="meta", model=cached.model, cached=True, provider_id=rp.provider_id)
        yield StreamEvent(type="delta", text=cached.response)
        yield StreamEvent(
            type="done",
            model=cached.model,
            cached=True,
            cost_jpy=D(cached.cost_jpy) if cached.cost_jpy else Decimal("0"),
            prompt_tokens=cached.prompt_tokens or 0,
            completion_tokens=cached.completion_tokens or 0,
            provider_id=rp.provider_id,
        )
        return

    priced = _is_priced(model)

    # 2. 预算检查（仅计价模型）
    guard = BudgetGuard(session)
    if priced:
        hist_len = sum(len(m.get("content", "")) for m in history)
        est_prompt = (len(user_content) + hist_len) // 3 + len(system_prompt) // 3
        est_cost = estimate_cost_jpy(model, est_prompt, max_tokens)
        guard.ensure(est_cost)  # 超限抛 BudgetExceeded

    yield StreamEvent(type="meta", model=model, cached=False, provider_id=rp.provider_id)

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
        for delta, final in providers.stream(
            rp, system_prompt=system_prompt, messages=messages, max_tokens=max_tokens
        ):
            if final is not None:
                prompt_tokens = final.prompt_tokens
                completion_tokens = final.completion_tokens
            elif delta:
                parts.append(delta)
                yield StreamEvent(type="delta", text=delta)
    except Exception as e:  # noqa: BLE001 — 网络/SDK 异常都要回传给前端
        log.error("ai.stream_error", error=str(e), prompt_type=prompt_type)
        yield StreamEvent(type="error", model=model, message=str(e))
        return

    # 末尾追加免责声明
    yield StreamEvent(type="delta", text=DISCLAIMER)
    text = "".join(parts) + DISCLAIMER

    cost = estimate_cost_jpy(model, prompt_tokens, completion_tokens) if priced else Decimal("0")

    # 写缓存
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

    if priced and guard.is_close():
        log.warning("ai.budget_close", ratio=round(guard.usage_ratio(), 2))

    yield StreamEvent(
        type="done",
        model=model,
        cached=False,
        cost_jpy=cost,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        provider_id=rp.provider_id,
    )
