"""财务/估值指标拉取 —— yfinance（美/港/日股）。

A 股 yfinance 覆盖有限，缺失时优雅留空（后续可接 AKShare 财务接口）。
所有数字转 Decimal 字符串入库，百分比统一存小数（0.15 = 15%）。
"""

from __future__ import annotations

from datetime import date

from app.core.money import D
from app.logging_config import get_logger
from app.services.data_sync.yfinance_client import YFinanceUnavailable, to_yf_symbol

log = get_logger(__name__)


def fetch_financials(symbol: str, market: str) -> dict | None:
    """拉取一只股票的财务/估值快照，返回字段字典（值为 Decimal 或 None）。"""
    try:
        import yfinance as yf  # noqa: PLC0415
    except ImportError as e:  # pragma: no cover
        raise YFinanceUnavailable("未安装 yfinance") from e

    ticker = to_yf_symbol(symbol, market)
    try:
        info = yf.Ticker(ticker).info
    except Exception as e:  # noqa: BLE001
        log.warning("financials.fetch_failed", ticker=ticker, error=str(e))
        return None

    if not info or not isinstance(info, dict):
        return None

    def _dec(key: str):  # noqa: ANN202
        v = info.get(key)
        if v is None:
            return None
        try:
            if v != v:  # NaN
                return None
        except TypeError:
            pass
        try:
            return D(str(v))
        except Exception:  # noqa: BLE001
            return None

    return {
        "as_of": date.today(),
        "pe": _dec("trailingPE"),
        "pb": _dec("priceToBook"),
        "roe": _dec("returnOnEquity"),  # 已是小数
        "revenue_yoy": _dec("revenueGrowth"),  # 小数
        "profit_yoy": _dec("earningsGrowth"),  # 小数
        "market_cap": _dec("marketCap"),
        "dividend_yield": _dec("dividendYield"),
        "eps": _dec("trailingEps"),
        "source": "yfinance",
    }
