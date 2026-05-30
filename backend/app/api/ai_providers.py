"""AI 服务商配置 API：CRUD + 拉取模型列表 + 连通性测试 + 设为默认。

API Key 出于安全只在写入时接收；列表/详情返回时做掩码（不回传明文）。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from app.core.response import Meta, ok
from app.database import get_session
from app.models.ai_provider import AiProvider
from app.models.base import utcnow
from app.services.ai import providers as provider_svc

router = APIRouter(prefix="/ai-providers", tags=["ai-providers"])


class ProviderCreate(BaseModel):
    name: str
    protocol: str = "openai"  # openai | anthropic
    base_url: str = ""
    api_key: str = ""
    models: list[str] = []
    default_model: str | None = None
    enabled: bool = True
    is_default: bool = False


class ProviderUpdate(BaseModel):
    name: str | None = None
    protocol: str | None = None
    base_url: str | None = None
    api_key: str | None = None  # 不传 = 不改；传空串 = 清空
    models: list[str] | None = None
    default_model: str | None = None
    enabled: bool | None = None
    is_default: bool | None = None


class ProbeRequest(BaseModel):
    """拉模型/测连接：可用已存 provider_id，或临时填参数（编辑中尚未保存时）。"""

    provider_id: int | None = None
    protocol: str | None = None
    base_url: str | None = None
    api_key: str | None = None
    model: str | None = None


def _mask(key: str) -> str:
    if not key:
        return ""
    if len(key) <= 8:
        return "••••"
    return f"{key[:4]}••••{key[-4:]}"


def _brief(p: AiProvider) -> dict:
    return {
        "id": p.id,
        "name": p.name,
        "protocol": p.protocol,
        "base_url": p.base_url,
        "api_key_mask": _mask(p.api_key),
        "has_key": bool(p.api_key),
        "models": p.models or [],
        "default_model": p.default_model,
        "enabled": p.enabled,
        "is_default": p.is_default,
        "updated_at": p.updated_at.isoformat() if p.updated_at else None,
    }


def _clear_other_defaults(session: Session, keep_id: int | None) -> None:
    for other in session.exec(select(AiProvider).where(AiProvider.is_default == True)).all():  # noqa: E712
        if other.id != keep_id:
            other.is_default = False
            session.add(other)


@router.get("", summary="服务商列表")
def list_providers(session: Session = Depends(get_session)) -> dict:
    rows = list(session.exec(select(AiProvider).order_by(AiProvider.id)).all())
    return ok([_brief(p) for p in rows], meta=Meta(total=len(rows)))


@router.post("", summary="新增服务商")
def create_provider(payload: ProviderCreate, session: Session = Depends(get_session)) -> dict:
    p = AiProvider(
        name=payload.name.strip() or "未命名",
        protocol=(payload.protocol or "openai").lower(),
        base_url=payload.base_url.strip(),
        api_key=payload.api_key.strip(),
        models=payload.models or [],
        default_model=payload.default_model,
        enabled=payload.enabled,
        is_default=payload.is_default,
    )
    session.add(p)
    session.flush()
    # 若设为默认，或这是第一个服务商 → 独占默认
    count = len(list(session.exec(select(AiProvider)).all()))
    if payload.is_default or count == 1:
        p.is_default = True
        _clear_other_defaults(session, p.id)
    session.commit()
    session.refresh(p)
    return ok(_brief(p))


@router.patch("/{provider_id}", summary="修改服务商")
def update_provider(
    provider_id: int, payload: ProviderUpdate, session: Session = Depends(get_session)
) -> dict:
    p = session.get(AiProvider, provider_id)
    if not p:
        raise HTTPException(status_code=404, detail="服务商不存在")
    if payload.name is not None:
        p.name = payload.name.strip() or p.name
    if payload.protocol is not None:
        p.protocol = payload.protocol.lower()
    if payload.base_url is not None:
        p.base_url = payload.base_url.strip()
    if payload.api_key is not None:
        p.api_key = payload.api_key.strip()
    if payload.models is not None:
        p.models = payload.models
    if payload.default_model is not None:
        p.default_model = payload.default_model or None
    if payload.enabled is not None:
        p.enabled = payload.enabled
    if payload.is_default is not None and payload.is_default:
        p.is_default = True
        _clear_other_defaults(session, p.id)
    elif payload.is_default is False:
        p.is_default = False
    p.updated_at = utcnow()
    session.add(p)
    session.commit()
    session.refresh(p)
    return ok(_brief(p))


@router.delete("/{provider_id}", summary="删除服务商")
def delete_provider(provider_id: int, session: Session = Depends(get_session)) -> dict:
    p = session.get(AiProvider, provider_id)
    if not p:
        raise HTTPException(status_code=404, detail="服务商不存在")
    was_default = p.is_default
    session.delete(p)
    session.flush()
    # 删除了默认服务商 → 选一个还在的当默认
    if was_default:
        nxt = session.exec(select(AiProvider).where(AiProvider.enabled == True).order_by(AiProvider.id)).first()  # noqa: E712
        if nxt:
            nxt.is_default = True
            session.add(nxt)
    session.commit()
    return ok({"deleted": provider_id})


@router.post("/{provider_id}/default", summary="设为默认服务商")
def set_default(provider_id: int, session: Session = Depends(get_session)) -> dict:
    p = session.get(AiProvider, provider_id)
    if not p:
        raise HTTPException(status_code=404, detail="服务商不存在")
    p.is_default = True
    p.enabled = True
    _clear_other_defaults(session, p.id)
    session.add(p)
    session.commit()
    session.refresh(p)
    return ok(_brief(p))


def _resolve_probe_params(
    session: Session, payload: ProbeRequest
) -> tuple[str, str | None, str]:
    """从已存 provider 或临时参数解析 protocol/base_url/api_key。"""
    protocol = payload.protocol
    base_url = payload.base_url
    api_key = payload.api_key
    if payload.provider_id is not None:
        p = session.get(AiProvider, payload.provider_id)
        if p:
            protocol = protocol or p.protocol
            base_url = base_url if base_url is not None else p.base_url
            # 未传 key 时用已存 key（编辑时不必重填）
            if not api_key:
                api_key = p.api_key
    return (protocol or "openai").lower(), base_url, api_key or ""


@router.post("/fetch-models", summary="拉取模型列表")
def fetch_models(payload: ProbeRequest, session: Session = Depends(get_session)) -> dict:
    protocol, base_url, api_key = _resolve_probe_params(session, payload)
    if not api_key:
        raise HTTPException(status_code=422, detail="缺少 API Key")
    try:
        models = provider_svc.fetch_models(protocol, base_url, api_key)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"拉取模型失败：{e}") from e
    return ok({"models": sorted(models)})


@router.post("/test", summary="测试连通性")
def test_connection(payload: ProbeRequest, session: Session = Depends(get_session)) -> dict:
    protocol, base_url, api_key = _resolve_probe_params(session, payload)
    if not api_key:
        raise HTTPException(status_code=422, detail="缺少 API Key")
    model = payload.model
    if not model and payload.provider_id is not None:
        p = session.get(AiProvider, payload.provider_id)
        if p:
            model = p.default_model or (p.models[0] if p.models else None)
    if not model:
        raise HTTPException(status_code=422, detail="缺少测试模型")
    okk, message = provider_svc.test_connection(protocol, base_url, api_key, model)
    return ok({"ok": okk, "message": message})
