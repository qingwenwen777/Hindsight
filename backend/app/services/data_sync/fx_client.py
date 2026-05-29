"""汇率同步 —— 通过 yfinance 拉取（USDJPY=X 等）。"""

from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlmodel import Session

from app.core.money import D
from app.logging_config import get_logger
from app.models.fx_rate import FxRate
from app.services.data_sync.base import safe_decimal
from app.services.data_sync.yfinance_client import YFinanceUnavailable, _import_yf

log = get_logger(__name__)

# 需要维护的货币对（base, quote） -> yfinance ticker
FX_PAIRS: list[tuple[str, str, str]] = [
    ("USD", "JPY", "USDJPY=X"),
    ("CNY", "JPY", "CNYJPY=X"),
    ("HKD", "JPY", "HKDJPY=X"),
    ("USD", "CNY", "USDCNY=X"),
    ("USD", "HKD", "USDHKD=X"),
]


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
