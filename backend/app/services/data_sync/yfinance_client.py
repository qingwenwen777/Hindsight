"""yfinance 客户端 —— 美股 / 港股 / 日股日线（默认复权 auto_adjust）。"""

from __future__ import annotations

import time
from datetime import date

from app.logging_config import get_logger
from app.services.data_sync.base import PriceBar, safe_decimal

log = get_logger(__name__)


class YFinanceUnavailable(Exception):
    """yfinance 不可用（未安装 / 网络 / 限流）。"""


def _import_yf():
    try:
        import yfinance as yf  # noqa: PLC0415

        return yf
    except ImportError as e:  # pragma: no cover
        raise YFinanceUnavailable("未安装 yfinance：pip install yfinance") from e


def to_yf_symbol(symbol: str, market: str) -> str:
    """把内部 symbol 映射为 yfinance ticker。

    - US: 直接用（AAPL）
    - HK: 4-5 位数字 + .HK（0700 -> 0700.HK；已带 .HK 则原样）
    - JP: 数字 + .T（7203 -> 7203.T）
    """
    market = market.upper()
    s = symbol.upper()
    if market == "US":
        return s
    if market == "HK":
        return s if s.endswith(".HK") else f"{s.zfill(4)}.HK"
    if market == "JP":
        return s if s.endswith(".T") else f"{s}.T"
    return s


def fetch_yf_daily(
    symbol: str,
    market: str,
    start: date | None = None,
    end: date | None = None,
    retries: int = 3,
    retry_delay: float = 1.5,
) -> list[PriceBar]:
    """拉取美/港/日股日线。"""
    yf = _import_yf()
    ticker = to_yf_symbol(symbol, market)
    start_str = start.isoformat() if start else "1990-01-01"
    end_str = end.isoformat() if end else date.today().isoformat()

    last_err: Exception | None = None
    df = None
    for attempt in range(1, retries + 1):
        try:
            df = yf.download(
                ticker,
                start=start_str,
                end=end_str,
                progress=False,
                auto_adjust=True,
            )
            break
        except Exception as e:  # noqa: BLE001
            last_err = e
            log.warning("yfinance.fetch_retry", ticker=ticker, attempt=attempt, error=str(e))
            if attempt < retries:
                time.sleep(retry_delay * attempt)
    else:
        raise YFinanceUnavailable(f"yfinance 拉取 {ticker} 失败：{last_err}") from last_err

    if df is None or df.empty:
        return []

    bars: list[PriceBar] = []
    # yfinance 多级列（Price, Ticker）；单 ticker 时用 .xs 或直接取列
    for idx, row in df.iterrows():
        d = idx.date() if hasattr(idx, "date") else date.fromisoformat(str(idx)[:10])

        def _get(col: str):
            # 兼容多级列与单级列
            try:
                val = row[col]
            except KeyError:
                try:
                    val = row[(col, ticker)]
                except (KeyError, TypeError):
                    return None
            # 若仍是 Series（多 ticker），取第一个
            if hasattr(val, "iloc"):
                val = val.iloc[0]
            return val

        vol_raw = _get("Volume")
        try:
            volume = int(vol_raw) if vol_raw is not None and vol_raw == vol_raw else None
        except (ValueError, TypeError):
            volume = None

        bars.append(
            PriceBar(
                date=d,
                open=safe_decimal(_get("Open")),
                high=safe_decimal(_get("High")),
                low=safe_decimal(_get("Low")),
                close=safe_decimal(_get("Close")),
                volume=volume,
            )
        )
    return bars
