"""AKShare 客户端 —— A 股日线（前复权）。

负责把 AKShare 返回的 DataFrame 标准化成 PriceBar 列表。
网络/依赖问题在此层捕获并抛出统一异常，由同步服务决定降级。
"""

from __future__ import annotations

import time
from datetime import date

from app.logging_config import get_logger
from app.services.data_sync.base import PriceBar, safe_decimal

log = get_logger(__name__)


class AkShareUnavailable(Exception):
    """AKShare 不可用（未安装 / 网络 / 限流）。"""


def _import_akshare():
    try:
        import akshare as ak  # noqa: PLC0415

        return ak
    except ImportError as e:  # pragma: no cover
        raise AkShareUnavailable("未安装 akshare：pip install akshare") from e


def fetch_cn_daily(
    symbol: str,
    start: date | None = None,
    end: date | None = None,
    adjust: str = "qfq",
    retries: int = 3,
    retry_delay: float = 1.5,
) -> list[PriceBar]:
    """拉取 A 股日线（默认前复权 qfq）。

    symbol 为 6 位代码（如 '600519'）。带重试与超时容错。
    """
    ak = _import_akshare()
    start_str = start.strftime("%Y%m%d") if start else "19900101"
    end_str = end.strftime("%Y%m%d") if end else date.today().strftime("%Y%m%d")

    last_err: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            df = ak.stock_zh_a_hist(
                symbol=symbol,
                period="daily",
                start_date=start_str,
                end_date=end_str,
                adjust=adjust,
            )
            break
        except Exception as e:  # noqa: BLE001
            last_err = e
            log.warning("akshare.fetch_retry", symbol=symbol, attempt=attempt, error=str(e))
            if attempt < retries:
                time.sleep(retry_delay * attempt)
    else:
        raise AkShareUnavailable(f"AKShare 拉取 {symbol} 失败：{last_err}") from last_err

    if df is None or df.empty:
        return []

    # AKShare A 股列名（中文）：日期/开盘/收盘/最高/最低/成交量/成交额/...
    col = {
        "date": "日期",
        "open": "开盘",
        "close": "收盘",
        "high": "最高",
        "low": "最低",
        "volume": "成交量",
        "turnover": "成交额",
    }
    bars: list[PriceBar] = []
    for _, row in df.iterrows():
        raw_date = row[col["date"]]
        # raw_date 可能是 str 或 Timestamp
        if hasattr(raw_date, "date"):
            d = raw_date.date()
        else:
            d = date.fromisoformat(str(raw_date)[:10])
        vol_raw = row.get(col["volume"])
        try:
            volume = int(vol_raw) if vol_raw is not None and vol_raw == vol_raw else None
        except (ValueError, TypeError):
            volume = None
        bars.append(
            PriceBar(
                date=d,
                open=safe_decimal(row.get(col["open"])),
                high=safe_decimal(row.get(col["high"])),
                low=safe_decimal(row.get(col["low"])),
                close=safe_decimal(row.get(col["close"])),
                volume=volume,
                turnover=safe_decimal(row.get(col["turnover"])),
            )
        )
    return bars
