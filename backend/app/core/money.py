"""金额 / Decimal 基础设施。

设计文档 v1.1 钦定：SQLite 不存浮点，所有金额/价格/数量用 TEXT 存储，
Python 侧统一用 Decimal 运算。本模块提供：

- `D(...)`：安全构造 Decimal（拒绝 float 直接入参，避免引入浮点误差）。
- `DecimalString`：SQLAlchemy TypeDecorator，DB 侧 TEXT ↔ Python 侧 Decimal。
- `Money`：金额 + 币种 的值对象（换算在 currency.py 中接入）。
- 量化辅助：货币按 2 位、数量按更高精度。
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Any

from sqlalchemy import String
from sqlalchemy.types import TypeDecorator

# 内部统一高精度上下文：金额计算用 Decimal，展示时再量化
MONEY_QUANT = Decimal("0.01")  # 货币展示精度（2 位）
QTY_QUANT = Decimal("0.00000001")  # 数量精度（8 位，兼容碎股/加密式精度）


def D(value: Any) -> Decimal:
    """安全构造 Decimal。

    - None → 抛错由调用方处理；这里对 None 返回 Decimal('0') 不合适，故显式拒绝。
    - float → 先转 str 再转 Decimal，避免 0.1 这类浮点污染（但仍记为可疑用法）。
    - int / str / Decimal → 直接构造。
    """
    if isinstance(value, Decimal):
        return value
    if isinstance(value, bool):  # bool 是 int 子类，显式排除
        raise TypeError("不能用 bool 构造 Decimal")
    if isinstance(value, int):
        return Decimal(value)
    if isinstance(value, float):
        # 浮点先转字符串，尽量减少误差；金额计算不应走这条路径
        return Decimal(str(value))
    if isinstance(value, str):
        s = value.strip()
        if s == "":
            raise InvalidOperation("空字符串不能转 Decimal")
        return Decimal(s)
    raise TypeError(f"不支持从 {type(value).__name__} 构造 Decimal")


def quantize_money(value: Decimal, places: Decimal = MONEY_QUANT) -> Decimal:
    """按货币精度四舍五入（银行家舍入不适用于报税，这里用 HALF_UP）。"""
    return value.quantize(places, rounding=ROUND_HALF_UP)


def to_db_str(value: Decimal | None) -> str | None:
    """Decimal → DB TEXT。保留原始精度，不预先量化。"""
    if value is None:
        return None
    return format(value, "f")  # 避免科学计数法


def from_db_str(value: str | None) -> Decimal | None:
    """DB TEXT → Decimal。"""
    if value is None:
        return None
    return Decimal(value)


class DecimalString(TypeDecorator):
    """SQLAlchemy 类型：DB 侧 TEXT，Python 侧 Decimal。

    用于所有金额/价格/数量列。写入时序列化为不含科学计数法的字符串，
    读取时还原为 Decimal，全程不经过 float。
    """

    impl = String
    cache_ok = True

    def process_bind_param(self, value: Any, dialect: Any) -> str | None:  # noqa: ARG002
        """Python → DB。"""
        if value is None:
            return None
        if not isinstance(value, Decimal):
            value = D(value)
        return to_db_str(value)

    def process_result_value(self, value: Any, dialect: Any) -> Decimal | None:  # noqa: ARG002
        """DB → Python。"""
        return from_db_str(value)


class Money:
    """金额值对象：amount(Decimal) + currency(str)。

    换算逻辑在 core/currency.py 中实现并注入，避免循环依赖。
    """

    __slots__ = ("amount", "currency")

    def __init__(self, amount: Any, currency: str) -> None:
        self.amount: Decimal = D(amount)
        self.currency: str = currency.upper()

    def __repr__(self) -> str:
        return f"Money({to_db_str(self.amount)} {self.currency})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Money):
            return NotImplemented
        return self.amount == other.amount and self.currency == other.currency

    def quantized(self, places: Decimal = MONEY_QUANT) -> Money:
        """返回按精度量化后的新 Money。"""
        return Money(quantize_money(self.amount, places), self.currency)
