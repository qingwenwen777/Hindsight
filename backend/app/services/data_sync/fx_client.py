"""汇率同步 —— 通过 yfinance 拉取（USDJPY=X 等）。"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import httpx
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlmodel import Session, select

from app.core.money import D
from app.logging_config import get_logger
from app.models.fx_rate import FxRate
from app.services.data_sync.base import safe_decimal
from app.services.data_sync.yfinance_client import YFinanceUnavailable, _import_yf

log = get_logger(__name__)

# 现金总览支持的四种货币
LIVE_CURRENCIES = ["USD", "JPY", "CNY", "HKD"]

# 需要维护的货币对（base, quote） -> yfinance ticker
FX_PAIRS: list[tuple[str, str, str]] = [
    ("USD", "JPY", "USDJPY=X"),
    ("CNY", "JPY", "CNYJPY=X"),
    ("HKD", "JPY", "HKDJPY=X"),
    ("USD", "CNY", "USDCNY=X"),
    ("USD", "HKD", "USDHKD=X"),
]


def fetch_live_usd_rates() -> dict[str, Decimal] | None:
    """从公开 API 拉取以 USD 为基准的实时汇率（rates[X] = 1 USD = X 单位）。

    数据源：open.er-api.com（免费、无需 key、每日更新）。失败返回 None。
    """
    try:
        resp = httpx.get("https://open.er-api.com/v6/latest/USD", timeout=10.0)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:  # noqa: BLE001
        log.warning("fx.live_fetch_failed", error=str(e))
        return None
    if data.get("result") != "success":
        log.warning("fx.live_bad_result", result=data.get("result"))
        return None
    rates = data.get("rates", {})
    out: dict[str, Decimal] = {}
    for c in LIVE_CURRENCIES:
        if c in rates:
            try:
                out[c] = D(str(rates[c]))
            except Exception:  # noqa: BLE001, S110
                pass
    return out if "USD" in out and len(out) >= 2 else None


def store_live_rates(session: Session, on_date: date | None = None) -> bool:
    """拉取实时汇率并写入 fx_rates（四种货币之间所有有向对）。返回是否成功。"""
    on_date = on_date or date.today()
    usd_rates = fetch_live_usd_rates()
    if not usd_rates:
        return False
    currencies = list(usd_rates.keys())
    for base in currencies:
        for quote in currencies:
            if base == quote:
                continue
            # 1 base = (quote per USD) / (base per USD) 单位 quote
            if usd_rates[base] == 0:
                continue
            rate = usd_rates[quote] / usd_rates[base]
            stmt = sqlite_insert(FxRate).values(
                date=on_date, base_currency=base, quote_currency=quote, rate=rate
            )
            stmt = stmt.on_conflict_do_update(
                index_elements=["date", "base_currency", "quote_currency"],
                set_={"rate": stmt.excluded.rate},
            )
            session.exec(stmt)
    session.commit()
    log.info("fx.live_stored", date=on_date.isoformat(), currencies=currencies)
    return True


def has_rates_for_date(session: Session, on_date: date) -> bool:
    """当天是否已有任意汇率记录。"""
    return session.exec(select(FxRate).where(FxRate.date == on_date).limit(1)).first() is not None


def sync_fx_rates(session: Session, *, days: int = 30) -> dict:
    """拉取近 days 天汇率并 UPSERT 到 fx_rates。"""
    yf = _import_yf()
    end = date.today()
    start = end - timedelta(days=days)
    summary = {"pairs": 0, "rows": 0, "failed": []}

    for base, quote, ticker in FX_PAIRS:
        try:
            df = yf.download(
                ticker, start=start.isoformat(), end=end.isoformat(), progress=False
            )
        except Exception as e:  # noqa: BLE001
            log.warning("fx.fetch_failed", ticker=ticker, error=str(e))
            summary["failed"].append(ticker)
            continue
        if df is None or df.empty:
            summary["failed"].append(ticker)
            continue

        rows = 0
        for idx, row in df.iterrows():
            d = idx.date() if hasattr(idx, "date") else date.fromisoformat(str(idx)[:10])
            close = row.get("Close")
            if hasattr(close, "iloc"):
                close = close.iloc[0]
            rate = safe_decimal(close)
            if rate is None:
                continue
            stmt = sqlite_insert(FxRate).values(
                date=d, base_currency=base, quote_currency=quote, rate=rate
            )
            stmt = stmt.on_conflict_do_update(
                index_elements=["date", "base_currency", "quote_currency"],
                set_={"rate": stmt.excluded.rate},
            )
            session.exec(stmt)
            rows += 1
        session.commit()
        summary["pairs"] += 1
        summary["rows"] += rows
        log.info("fx.pair_done", pair=f"{base}/{quote}", rows=rows)

    return summary


def upsert_fx_rate(
    session: Session, base: str, quote: str, on_date: date, rate: str
) -> None:
    """手动写入一条汇率（测试/补录用）。"""
    stmt = sqlite_insert(FxRate).values(
        date=on_date, base_currency=base.upper(), quote_currency=quote.upper(), rate=D(rate)
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=["date", "base_currency", "quote_currency"],
        set_={"rate": stmt.excluded.rate},
    )
    session.exec(stmt)
    session.commit()
