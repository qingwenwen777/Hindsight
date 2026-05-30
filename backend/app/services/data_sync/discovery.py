"""股票发现 —— 通过 yfinance 搜索把"代码/名称"映射成可登记的候选。

用于"搜索时自动从数据源发现股票"：本地库查不到时，调用 yfinance 的 Search
接口，按交易所/后缀归一化成内部 (symbol, market, currency)，过滤到本平台支持
的四个市场（US/HK/JP/CN），供前端一键登记 + 同步。
"""

from __future__ import annotations

from dataclasses import dataclass, asdict

from app.logging_config import get_logger
from app.services.data_sync.yfinance_client import YFinanceUnavailable

log = get_logger(__name__)

# 市场 -> 计价币种
MARKET_CURRENCY = {
    "US": "USD",
    "HK": "HKD",
    "JP": "JPY",
    "CN": "CNY",
}

# yfinance 交易所代码 -> 市场（无后缀的美股用得上）
_US_EXCHANGES = {"NMS", "NYQ", "NGM", "NCM", "NIM", "PCX", "ASE", "BATS", "NYS"}


@dataclass
class Candidate:
    """一个可登记的候选股票（尚未写库）。"""

    symbol: str  # 内部 symbol（去掉 yfinance 后缀，如 7203 / 0700 / 600519 / AAPL）
    market: str  # US / HK / JP / CN
    name: str
    currency: str
    exchange: str  # 交易所展示名
    quote_type: str  # EQUITY / ETF
    yf_symbol: str  # yfinance 原始 ticker（AAPL / 7203.T / 0700.HK / 600519.SS）


def _normalize(quote: dict) -> Candidate | None:
    """把一条 yfinance 搜索结果归一化成 Candidate；不支持的市场返回 None。"""
    yf_symbol = (quote.get("symbol") or "").strip()
    if not yf_symbol:
        return None

    quote_type = (quote.get("quoteType") or "").upper()
    if quote_type not in ("EQUITY", "ETF"):
        return None

    name = quote.get("shortname") or quote.get("longname") or yf_symbol
    name = str(name).strip()
    exch_disp = quote.get("exchDisp") or quote.get("exchange") or ""
    exch_code = (quote.get("exchange") or "").upper()

    s = yf_symbol.upper()
    market: str | None = None
    internal = s

    if s.endswith(".T"):
        market, internal = "JP", s[:-2]
    elif s.endswith(".HK"):
        market, internal = "HK", s[:-3].zfill(4)
    elif s.endswith(".SS") or s.endswith(".SZ"):
        market, internal = "CN", s[:-3]
    elif "." not in s and exch_code in _US_EXCHANGES:
        market, internal = "US", s

    if market is None:
        return None

    return Candidate(
        symbol=internal,
        market=market,
        name=name,
        currency=MARKET_CURRENCY[market],
        exchange=str(exch_disp),
        quote_type=quote_type,
        yf_symbol=yf_symbol,
    )


def discover_symbols(
    q: str, market: str | None = None, limit: int = 8
) -> list[dict]:
    """按关键字（代码或名称）从 yfinance 发现候选股票。

    返回去重后的候选列表（dict），仅含本平台支持的市场。
    """
    q = (q or "").strip()
    if len(q) < 2:
        return []

    try:
        import yfinance as yf  # noqa: PLC0415
    except ImportError as e:  # pragma: no cover
        raise YFinanceUnavailable("未安装 yfinance") from e

    try:
        # 多取一些原始结果，归一化/过滤后再截断
        search = yf.Search(q, max_results=max(limit * 3, 10))
        raw_quotes = search.quotes or []
    except Exception as e:  # noqa: BLE001
        log.warning("discovery.search_failed", q=q, error=str(e))
        raise YFinanceUnavailable(f"数据源搜索失败：{e}") from e

    target_market = market.upper() if market else None
    seen: set[tuple[str, str]] = set()
    out: list[dict] = []
    for quote in raw_quotes:
        cand = _normalize(quote)
        if cand is None:
            continue
        if target_market and cand.market != target_market:
            continue
        key = (cand.symbol, cand.market)
        if key in seen:
            continue
        seen.add(key)
        out.append(asdict(cand))
        if len(out) >= limit:
            break
    return out
