"""行情同步公共结构：标准化的日线 bar、同步结果、数据校验。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from app.core.money import D


@dataclass
class PriceBar:
    """标准化日线（原始数据源差异在 client 内消化）。"""

    date: date
    open: Decimal | None
    high: Decimal | None
    low: Decimal | None
    close: Decimal
    volume: int | None = None
    turnover: Decimal | None = None
    adjust_factor: Decimal | None = None


@dataclass
class SyncResult:
    """单只股票一次同步的结果。"""

    symbol: str
    market: str
    inserted: int = 0
    updated: int = 0
    skipped: int = 0
    ok: bool = True
    message: str = ""
    source: str = ""


@dataclass
class SyncReport:
    """一次批量同步的汇总。"""

    market: str
    results: list[SyncResult] = field(default_factory=list)

    @property
    def total_inserted(self) -> int:
        return sum(r.inserted for r in self.results)

    @property
    def total_updated(self) -> int:
        return sum(r.updated for r in self.results)

    @property
    def failed(self) -> list[SyncResult]:
        return [r for r in self.results if not r.ok]

    @property
    def fail_ratio(self) -> float:
        if not self.results:
            return 0.0
        return len(self.failed) / len(self.results)


class PriceValidationError(Exception):
    """行情数据校验失败。"""


def validate_bar(bar: PriceBar) -> None:
    """校验单根 bar（设计文档 5.1）：

    - 价格非负
    - high >= low
    - open/close 落在 [low, high] 区间
    """
    prices = {
        "open": bar.open,
        "high": bar.high,
        "low": bar.low,
        "close": bar.close,
    }
    for name, v in prices.items():
        if v is not None and v < 0:
            raise PriceValidationError(f"{bar.date} {name} 为负：{v}")
    if bar.high is not None and bar.low is not None and bar.high < bar.low:
        raise PriceValidationError(f"{bar.date} high<low：{bar.high}<{bar.low}")
    if bar.high is not None and bar.low is not None:
        for name in ("open", "close"):
            v = prices[name]
            if v is not None and not (bar.low <= v <= bar.high):
                raise PriceValidationError(
                    f"{bar.date} {name}={v} 不在 [{bar.low}, {bar.high}] 区间"
                )
    if bar.volume is not None and bar.volume < 0:
        raise PriceValidationError(f"{bar.date} volume 为负：{bar.volume}")


def safe_decimal(value) -> Decimal | None:  # noqa: ANN001
    """把数据源的数值安全转 Decimal（None/NaN → None）。"""
    if value is None:
        return None
    try:
        # pandas 的 NaN
        if value != value:  # noqa: PLR0124  NaN != NaN
            return None
    except TypeError:
        pass
    s = str(value).strip()
    if s == "" or s.lower() in ("nan", "none"):
        return None
    return D(s)
