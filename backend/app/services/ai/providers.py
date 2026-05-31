"""AI 服务商解析与底层调用 —— 统一封装 OpenAI / Anthropic 两种协议。

职责：
- 解析"用哪个服务商 + 哪个模型"（显式指定 > 全局默认 > env 兜底）。
- 提供统一的同步调用与流式调用接口，屏蔽两种 SDK 差异。
- 拉取模型列表、测试连通性。
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass

from sqlmodel import Session, select

from app.config import settings
from app.logging_config import get_logger
from app.models.ai_provider import AiProvider

log = get_logger(__name__)


@dataclass
class ResolvedProvider:
    """一次调用最终落定的服务商 + 模型。"""

    protocol: str  # openai | anthropic
    base_url: str | None
    api_key: str
    model: str
    provider_id: int | None
    provider_name: str


@dataclass
class LlmResult:
    text: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    # 结束原因：normal / length（命中 max_tokens 截断）/ 其他
    finish_reason: str | None = None


class ProviderUnavailable(Exception):
    """无可用服务商（既无 DB 配置也无 env 兜底）。"""


def _env_fallback(model_override: str | None) -> ResolvedProvider | None:
    """env 兜底：沿用旧的 ANTHROPIC_API_KEY / AI_BASE_URL / AI_MODEL。"""
    if not settings.anthropic_api_key:
        return None
    return ResolvedProvider(
        protocol="anthropic",
        base_url=settings.ai_base_url or None,
        api_key=settings.anthropic_api_key,
        model=model_override or settings.ai_model or "claude-sonnet-4-5",
        provider_id=None,
        provider_name="env",
    )


def get_default_provider(session: Session) -> AiProvider | None:
    """全局默认服务商：优先 is_default，其次第一个 enabled。"""
    p = session.exec(
        select(AiProvider).where(AiProvider.is_default == True, AiProvider.enabled == True)  # noqa: E712
    ).first()
    if p:
        return p
    return session.exec(
        select(AiProvider).where(AiProvider.enabled == True).order_by(AiProvider.id)  # noqa: E712
    ).first()


def resolve(
    session: Session,
    *,
    provider_id: int | None = None,
    model: str | None = None,
) -> ResolvedProvider | None:
    """解析最终使用的服务商与模型。

    优先级：显式 provider_id > 全局默认服务商 > env 兜底。
    model：显式 model > 服务商 default_model > 服务商 models[0]。
    """
    provider: AiProvider | None = None
    if provider_id is not None:
        provider = session.get(AiProvider, provider_id)
    if provider is None:
        provider = get_default_provider(session)

    if provider is None:
        return _env_fallback(model)

    chosen_model = model or provider.default_model or (provider.models[0] if provider.models else None)
    if not chosen_model:
        # 服务商没配模型 → 尝试 env 兜底
        return _env_fallback(model)

    return ResolvedProvider(
        protocol=(provider.protocol or "openai").lower(),
        base_url=provider.base_url or None,
        api_key=provider.api_key or "",
        model=chosen_model,
        provider_id=provider.id,
        provider_name=provider.name,
    )


def has_any_provider(session: Session) -> bool:
    """是否存在可用服务商（DB 有 enabled 的，或 env 兜底可用）。"""
    if get_default_provider(session) is not None:
        return True
    return _env_fallback(None) is not None


def seed_default_from_env(session: Session) -> None:
    """首次启动：若 DB 无任何服务商，但 env 配了 key，则把 env 配置迁为默认服务商。

    env 用的是 Anthropic 兼容端点（如 DeepSeek 的 /anthropic）。迁移后用户即可在
    前端「AI 配置」里管理；env 仍作为最终兜底。
    """
    existing = session.exec(select(AiProvider).limit(1)).first()
    if existing is not None:
        return
    if not settings.anthropic_api_key:
        return
    model = settings.ai_model or "deepseek-chat"
    name = "DeepSeek" if settings.ai_base_url and "deepseek" in settings.ai_base_url else "默认服务商"
    provider = AiProvider(
        name=name,
        protocol="anthropic",
        base_url=settings.ai_base_url or "",
        api_key=settings.anthropic_api_key,
        models=[model],
        default_model=model,
        is_default=True,
        enabled=True,
    )
    session.add(provider)
    session.commit()
    log.info("ai.provider_seeded", name=name, model=model)


# ---------- 底层调用（屏蔽两种协议差异）----------


def _anthropic_client(rp: ResolvedProvider):  # noqa: ANN202
    import anthropic  # noqa: PLC0415

    kwargs: dict = {"api_key": rp.api_key}
    if rp.base_url:
        kwargs["base_url"] = rp.base_url
    return anthropic.Anthropic(**kwargs)


def _openai_client(rp: ResolvedProvider):  # noqa: ANN202
    import openai  # noqa: PLC0415

    kwargs: dict = {"api_key": rp.api_key}
    if rp.base_url:
        kwargs["base_url"] = rp.base_url
    return openai.OpenAI(**kwargs)


def call(
    rp: ResolvedProvider,
    *,
    system_prompt: str,
    messages: list[dict],
    max_tokens: int,
) -> LlmResult:
    """同步调用，返回完整文本与用量。messages 为 [{role, content}]（不含 system）。"""
    if rp.protocol == "anthropic":
        client = _anthropic_client(rp)
        msg = client.messages.create(
            model=rp.model,
            max_tokens=max_tokens,
            system=system_prompt,
            messages=messages,
        )
        text = "".join(b.text for b in msg.content if getattr(b, "type", None) == "text")
        return LlmResult(
            text=text,
            model=rp.model,
            prompt_tokens=msg.usage.input_tokens,
            completion_tokens=msg.usage.output_tokens,
            finish_reason="length" if getattr(msg, "stop_reason", None) == "max_tokens" else "normal",
        )
    # openai 兼容
    client = _openai_client(rp)
    oai_messages = [{"role": "system", "content": system_prompt}, *messages]
    resp = client.chat.completions.create(
        model=rp.model,
        max_tokens=max_tokens,
        messages=oai_messages,
    )
    text = resp.choices[0].message.content or ""
    usage = resp.usage
    return LlmResult(
        text=text,
        model=rp.model,
        prompt_tokens=getattr(usage, "prompt_tokens", 0) or 0,
        completion_tokens=getattr(usage, "completion_tokens", 0) or 0,
        finish_reason=getattr(resp.choices[0], "finish_reason", None),
    )


def stream(
    rp: ResolvedProvider,
    *,
    system_prompt: str,
    messages: list[dict],
    max_tokens: int,
) -> Iterator[tuple[str, LlmResult | None]]:
    """流式调用。产出 (delta_text, None)；结束时产出 ("", LlmResult) 携带用量。"""
    if rp.protocol == "anthropic":
        client = _anthropic_client(rp)
        with client.messages.stream(
            model=rp.model,
            max_tokens=max_tokens,
            system=system_prompt,
            messages=messages,
        ) as s:
            for text in s.text_stream:
                if text:
                    yield text, None
            final = s.get_final_message()
        yield "", LlmResult(
            text="",
            model=rp.model,
            prompt_tokens=final.usage.input_tokens,
            completion_tokens=final.usage.output_tokens,
            finish_reason="length" if getattr(final, "stop_reason", None) == "max_tokens" else "normal",
        )
        return

    # openai 兼容流式
    client = _openai_client(rp)
    oai_messages = [{"role": "system", "content": system_prompt}, *messages]
    stream_obj = client.chat.completions.create(
        model=rp.model,
        max_tokens=max_tokens,
        messages=oai_messages,
        stream=True,
        stream_options={"include_usage": True},
    )
    prompt_tokens = 0
    completion_tokens = 0
    finish_reason: str | None = None
    for chunk in stream_obj:
        if chunk.usage:
            prompt_tokens = chunk.usage.prompt_tokens or 0
            completion_tokens = chunk.usage.completion_tokens or 0
        if chunk.choices:
            choice = chunk.choices[0]
            if getattr(choice, "finish_reason", None):
                finish_reason = choice.finish_reason
            delta = choice.delta
            piece = getattr(delta, "content", None)
            if piece:
                yield piece, None
    yield "", LlmResult(
        text="",
        model=rp.model,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        finish_reason=finish_reason,
    )


# ---------- 模型列表 / 连通性 ----------


def fetch_models(protocol: str, base_url: str | None, api_key: str) -> list[str]:
    """拉取服务商可用模型列表。失败抛异常由调用方处理。"""
    protocol = (protocol or "openai").lower()
    rp = ResolvedProvider(
        protocol=protocol, base_url=base_url or None, api_key=api_key, model="",
        provider_id=None, provider_name="probe",
    )
    if protocol == "anthropic":
        client = _anthropic_client(rp)
        page = client.models.list(limit=1000)
        return [m.id for m in page.data]
    client = _openai_client(rp)
    page = client.models.list()
    return [m.id for m in page.data]


def test_connection(
    protocol: str, base_url: str | None, api_key: str, model: str
) -> tuple[bool, str]:
    """发一个最小请求测试连通性。返回 (ok, message)。"""
    rp = ResolvedProvider(
        protocol=(protocol or "openai").lower(), base_url=base_url or None,
        api_key=api_key, model=model, provider_id=None, provider_name="test",
    )
    try:
        result = call(
            rp,
            system_prompt="You are a connection test. Reply with 'ok'.",
            messages=[{"role": "user", "content": "ping"}],
            max_tokens=8,
        )
        return True, (result.text or "ok").strip()[:80]
    except Exception as e:  # noqa: BLE001
        return False, str(e)[:200]
