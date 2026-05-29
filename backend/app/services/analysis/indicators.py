"""技术指标 —— 自实现，不依赖 pandas-ta（其与 numpy 2.x 不兼容）。

实现：MA、EMA、MACD、RSI（Wilder）、布林带、KDJ。
输入为收盘价/高低价序列（list[float] 或 pandas Series），输出 dict[str, list]。
计算用 float（指标是统计量，非金额，不要求 Decimal 精度）。
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def _series(values: list[float]) -> pd.Series:
    return pd.Series([float(v) for v in values], dtype="float64")


def _round_list(s: pd.Series, digits: int = 4) -> list[float | None]:
    """把 Series 转为 list，NaN → None，保留 digits 位。"""
    return [None if pd.isna(v) else round(float(v), digits) for v in s]


def ma(close: list[float], period: int = 20) -> list[float | None]:
    """简单移动平均。"""
    return _round_list(_series(close).rolling(window=period, min_periods=period).mean())


def ema(close: list[float], period: int = 20) -> list[float | None]:
    """指数移动平均。"""
    return _round_list(_series(close).ewm(span=period, adjust=False).mean())


def macd(
    close: list[float], fast: int = 12, slow: int = 26, signal: int = 9
) -> dict[str, list[float | None]]:
    """MACD：DIF(快慢 EMA 差)、DEA(DIF 的信号 EMA)、柱(2*(DIF-DEA))。"""
    s = _series(close)
    ema_fast = s.ewm(span=fast, adjust=False).mean()
    ema_slow = s.ewm(span=slow, adjust=False).mean()
    dif = ema_fast - ema_slow
    dea = dif.ewm(span=signal, adjust=False).mean()
    hist = (dif - dea) * 2
    return {
        "dif": _round_list(dif),
        "dea": _round_list(dea),
        "hist": _round_list(hist),
    }


def rsi(close: list[float], period: int = 14) -> list[float | None]:
    """RSI（Wilder 平滑）。"""
    s = _series(close)
    delta = s.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    # Wilder 平滑：用 alpha=1/period 的 EWM
    avg_gain = gain.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    rs = avg_gain / avg_loss
    result = 100 - (100 / (1 + rs))
    # 当 avg_loss=0 时 RSI=100
    result = result.where(avg_loss != 0, 100.0)
    # 前 period 个为 NaN
    result[: period] = np.nan
    return _round_list(result, digits=2)


def bollinger(
    close: list[float], period: int = 20, num_std: float = 2.0
) -> dict[str, list[float | None]]:
    """布林带：中轨(MA)、上轨、下轨。"""
    s = _series(close)
    mid = s.rolling(window=period, min_periods=period).mean()
    std = s.rolling(window=period, min_periods=period).std(ddof=0)
    upper = mid + num_std * std
    lower = mid - num_std * std
    return {
        "mid": _round_list(mid),
        "upper": _round_list(upper),
        "lower": _round_list(lower),
    }


def kdj(
    high: list[float], low: list[float], close: list[float], period: int = 9
) -> dict[str, list[float | None]]:
    """KDJ：RSV → K(SMA) → D(SMA) → J=3K-2D。"""
    h = _series(high)
    low_s = _series(low)
    c = _series(close)
    lowest = low_s.rolling(window=period, min_periods=period).min()
    highest = h.rolling(window=period, min_periods=period).max()
    rsv = (c - lowest) / (highest - lowest) * 100
    rsv = rsv.replace([np.inf, -np.inf], np.nan).fillna(50)
    # K、D 用 alpha=1/3 的递推（等价传统 SMA(3) 口径）
    k = rsv.ewm(alpha=1 / 3, adjust=False).mean()
    d = k.ewm(alpha=1 / 3, adjust=False).mean()
    j = 3 * k - 2 * d
    # period 之前无意义，置 None
    k[: period - 1] = np.nan
    d[: period - 1] = np.nan
    j[: period - 1] = np.nan
    return {
        "k": _round_list(k, 2),
        "d": _round_list(d, 2),
        "j": _round_list(j, 2),
    }


def compute_indicators(
    close: list[float],
    high: list[float] | None = None,
    low: list[float] | None = None,
    types: list[str] | None = None,
) -> dict:
    """按需计算多个指标。types 为空则全算（KDJ 需要 high/low）。"""
    types = types or ["MA", "EMA", "MACD", "RSI", "BOLL", "KDJ"]
    out: dict = {}
    for t in (x.upper() for x in types):
        if t == "MA":
            out["ma"] = {f"ma{p}": ma(close, p) for p in (5, 10, 20, 60)}
        elif t == "EMA":
            out["ema"] = {f"ema{p}": ema(close, p) for p in (12, 26)}
        elif t == "MACD":
            out["macd"] = macd(close)
        elif t == "RSI":
            out["rsi"] = {"rsi14": rsi(close, 14)}
        elif t in ("BOLL", "BOLLINGER"):
            out["boll"] = bollinger(close)
        elif t == "KDJ":
            if high is not None and low is not None:
                out["kdj"] = kdj(high, low, close)
    return out
