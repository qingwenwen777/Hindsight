"""模型公共基类与枚举。"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum


def utcnow() -> datetime:
    """统一的 UTC 时间戳（存储一律 UTC）。"""
    return datetime.now(timezone.utc)


# ---- 枚举（用 str Enum 便于 JSON 序列化与 DB 存储）----


class Market(str, Enum):
    """市场。"""

    CN = "CN"
    US = "US"
    HK = "HK"
    JP = "JP"


class Currency(str, Enum):
    """币种。"""

    CNY = "CNY"
    USD = "USD"
    HKD = "HKD"
    JPY = "JPY"


class TransactionType(str, Enum):
    """交易类型（仅买/卖，公司行动与分红分表）。"""

    BUY = "BUY"
    SELL = "SELL"


class CorporateActionType(str, Enum):
    """公司行动类型。"""

    SPLIT = "SPLIT"
    BONUS = "BONUS"
    RIGHTS = "RIGHTS"
    MERGE = "MERGE"


class DecisionType(str, Enum):
    """决策类型。"""

    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"
    WATCH = "WATCH"


class ThesisCategory(str, Enum):
    """投资论点类别。"""

    VALUATION = "VALUATION"
    TREND = "TREND"
    EVENT = "EVENT"
    GROWTH = "GROWTH"
    OTHER = "OTHER"


class Horizon(str, Enum):
    """预期持有时间。"""

    SHORT = "SHORT"
    MEDIUM = "MEDIUM"
    LONG = "LONG"


class Emotion(str, Enum):
    """决策时情绪。"""

    CALM = "CALM"
    HESITANT = "HESITANT"
    FOMO = "FOMO"
    PANIC = "PANIC"
    REVENGE = "REVENGE"


class CashFlowType(str, Enum):
    """现金流类型。"""

    DEPOSIT = "DEPOSIT"
    WITHDRAW = "WITHDRAW"
    DIVIDEND = "DIVIDEND"
    INTEREST = "INTEREST"
    TRADE_BUY = "TRADE_BUY"
    TRADE_SELL = "TRADE_SELL"
    FEE = "FEE"
    TAX = "TAX"
    FX = "FX"
