"""AI 服务商配置模型：支持 OpenAI / Anthropic 两种协议格式。"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Column
from sqlalchemy.types import JSON
from sqlmodel import Field, SQLModel

from app.models.base import utcnow


class AiProvider(SQLModel, table=True):
    """用户配置的 AI 服务商（ai_providers 表）。

    protocol:
      - "openai"    : OpenAI 兼容端点（/v1/chat/completions），用 openai SDK 调用
      - "anthropic" : Anthropic 兼容端点（/v1/messages），用 anthropic SDK 调用
    base_url 填到 /v1 这一层（例如 https://api.openai.com/v1）。
    models 为该服务商下可用模型名列表。
    is_default 标记全局默认服务商（对话/分析未指定时用它）。
    """

    __tablename__ = "ai_providers"

    id: int | None = Field(default=None, primary_key=True)
    name: str
    protocol: str = "openai"  # openai | anthropic
    base_url: str = ""
    api_key: str = ""
    models: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    default_model: str | None = None  # 该服务商默认用的模型
    is_default: bool = False
    enabled: bool = True
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


__all__ = ["AiProvider"]
