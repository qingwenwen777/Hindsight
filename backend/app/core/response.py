"""统一响应壳：{ code, message, data, meta }（设计文档第 6 章）。"""

from __future__ import annotations

from typing import Any, Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class Meta(BaseModel):
    """分页/附加元信息。"""

    page: int | None = None
    page_size: int | None = None
    total: int | None = None


class ApiResponse(BaseModel, Generic[T]):
    """统一响应壳。code=0 表示成功，非 0 表示业务错误。"""

    code: int = 0
    message: str = "ok"
    data: T | None = None
    meta: Meta | None = None


def ok(data: Any = None, message: str = "ok", meta: Meta | None = None) -> dict[str, Any]:
    """构造成功响应字典（便于直接返回，避免泛型序列化坑）。"""
    return {"code": 0, "message": message, "data": data, "meta": meta}


def fail(code: int, message: str, data: Any = None) -> dict[str, Any]:
    """构造失败响应字典。"""
    return {"code": code, "message": message, "data": data, "meta": None}
