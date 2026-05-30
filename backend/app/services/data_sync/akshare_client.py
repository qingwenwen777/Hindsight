"""AKShare 客户端 —— A 股日线（前复权）。

负责把 AKShare 返回的 DataFrame 标准化成 PriceBar 列表。
网络/依赖问题在此层捕获并抛出统一异常，由同步服务决定降级。

数据源容错：东方财富(stock_zh_a_hist) 在部分海外服务器被屏蔽，因此按
新浪(stock_zh_a_daily，含成交量) -> 腾讯(stock_zh_a_hist_tx) -> 东方财富
的顺序依次尝试，任一成功即返回。
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


def _prefixed_symbol(symbol: str) -> str:
    """6 位代码转带交易所前缀（sh/sz），供新浪/腾讯接口使用。

    上交所：60xxxx(主板) / 68xxxx(科创板) / 9xxxxx(B股) -> sh
    深交所：00xxxx / 30xxxx(创业板) / 200xxx(B股) -> sz
    """
    s = symbol.lower()
    if s.startswith(("sh", "sz")):
        return s
    code = s.zfill(6)
    return f"sh{code}" if code[0] in ("6", "9") else f"sz{code}"


def _bars_from_df(df, colmap: dict[str, str]) -> list[PriceBar]:
    """按列名映射把 DataFrame 转成 PriceBar 列表（缺列则置 None）。"""
    bars: list[PriceBar] = []
    for _, row in df.iterrows():
        raw_date = row[colmap["date"]]
        if hasattr(raw_date, "date"):
            d = raw_date.date()
        else:
            d = date.fromisoformat(str(raw_date)[:10])

        volume = None
        vcol = colmap.get("volume")
        if vcol and vcol in row:
            vol_raw = row.get(vcol)
            try:
                volume = int(float(vol_raw)) if vol_raw is not None and vol_raw == vol_raw else None
            except (ValueError, TypeError):
                volume = None

        tcol = colmap.get("turnover")
        turnover = safe_decimal(row.get(tcol)) if tcol and tcol in row else None

        bars.append(
            PriceBar(
                date=d,
                open=safe_decimal(row.get(colmap["open"])),
                high=safe_decimal(row.get(colmap["high"])),
                low=safe_decimal(row.get(colmap["low"])),
                close=safe_decimal(row.get(colmap["close"])),
                volume=volume,
                turnover=turnover,
            )
        )
    return bars


def _fetch_sina(ak, symbol: str, start_str: str, end_str: str, adjust: str):  # noqa: ANN001
    """新浪源：stock_zh_a_daily（含成交量），symbol 需带 sh/sz 前缀。"""
    df = ak.stock_zh_a_daily(
        symbol=_prefixed_symbol(symbol), start_date=start_str, end_date=end_str, adjust=adjust
    )
    if df is None or df.empty:
        return []
    return _bars_from_df(
        df,
        {
            "date": "date",
            "open": "open",
            "high": "high",
            "low": "low",
            "close": "close",
            "volume": "volume",
            "turnover": "amount",
        },
    )


def _fetch_tencent(ak, symbol: str, start_str: str, end_str: str, adjust: str):  # noqa: ANN001
    """腾讯源：stock_zh_a_hist_tx（无成交量），symbol 需带 sh/sz 前缀。"""
    df = ak.stock_zh_a_hist_tx(
        symbol=_prefixed_symbol(symbol), start_date=start_str, end_date=end_str, adjust=adjust
    )
    if df is None or df.empty:
        return []
    return _bars_from_df(
        df,
        {
            "date": "date",
            "open": "open",
            "high": "high",
            "low": "low",
            "close": "close",
            "turnover": "amount",
        },
    )


def _fetch_eastmoney(ak, symbol: str, start_str: str, end_str: str, adjust: str):  # noqa: ANN001
    """东方财富源：stock_zh_a_hist（中文列名），symbol 为 6 位代码。"""
    code = symbol.lower().removeprefix("sh").removeprefix("sz").zfill(6)
    df = ak.stock_zh_a_hist(
        symbol=code, period="daily", start_date=start_str, end_date=end_str, adjust=adjust
    )
    if df is None or df.empty:
        return []
    return _bars_from_df(
        df,
        {
            "date": "日期",
            "open": "开盘",
            "high": "最高",
            "low": "最低",
            "close": "收盘",
            "volume": "成交量",
            "turnover": "成交额",
        },
    )


# 源优先级：新浪(含量) -> 腾讯 -> 东方财富
_CN_SOURCES = (
    ("sina", _fetch_sina),
    ("tencent", _fetch_tencent),
    ("eastmoney", _fetch_eastmoney),
)


def fetch_cn_daily(
    symbol: str,
    start: date | None = None,
    end: date | None = None,
    adjust: str = "qfq",
    retries: int = 2,
    retry_delay: float = 1.0,
) -> list[PriceBar]:
    """拉取 A 股日线（默认前复权 qfq）。

    symbol 为 6 位代码（如 '600519'）。按多源优先级容错，每源带重试。
    """
    ak = _import_akshare()
    start_str = start.strftime("%Y%m%d") if start else "19900101"
    end_str = end.strftime("%Y%m%d") if end else date.today().strftime("%Y%m%d")

    errors: list[str] = []
    for source_name, fetch_fn in _CN_SOURCES:
        last_err: Exception | None = None
        for attempt in range(1, retries + 1):
            try:
                bars = fetch_fn(ak, symbol, start_str, end_str, adjust)
                if bars:
                    log.info("akshare.fetch_ok", symbol=symbol, source=source_name, bars=len(bars))
                    return bars
                # 空结果：不再重试该源，换下一源
                break
            except Exception as e:  # noqa: BLE001
                last_err = e
                log.warning(
                    "akshare.fetch_retry",
                    symbol=symbol,
                    source=source_name,
                    attempt=attempt,
                    error=str(e),
                )
                if attempt < retries:
                    time.sleep(retry_delay * attempt)
        if last_err is not None:
            errors.append(f"{source_name}: {last_err}")

    if errors:
        raise AkShareUnavailable(
            f"AKShare 拉取 {symbol} 失败（全部源）：" + " | ".join(errors)
        )
    # 所有源都返回空（无数据）
    return []
