"""行情同步服务 —— 增量同步 + 校验 + UPSERT。"""

from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlmodel import Session, select

from app.logging_config import get_logger
from app.models.stock import Price, Stock
from app.services.data_sync.akshare_client import AkShareUnavailable, fetch_cn_daily
from app.services.data_sync.base import (
    PriceBar,
    PriceValidationError,
    SyncReport,
    SyncResult,
    validate_bar,
)

log = get_logger(__name__)


def _latest_price_date(session: Session, stock_id: int) -> date | None:
    """查某股票已有行情的最新日期（用于增量同步）。"""
    stmt = select(Price.date).where(Price.stock_id == stock_id).order_by(Price.date.desc()).limit(1)
    return session.exec(stmt).first()


def _upsert_bars(session: Session, stock_id: int, bars: list[PriceBar]) -> tuple[int, int, int]:
    """UPSERT 一批 bar，返回 (inserted, updated, skipped)。

    用 SQLite ON CONFLICT(stock_id, date) DO UPDATE 实现幂等，重复同步不产生重复行。
    """
    inserted = updated = skipped = 0
    # 先查已有日期集合，用于区分 insert / update 计数
    existing_dates: set[date] = set(
        session.exec(select(Price.date).where(Price.stock_id == stock_id)).all()
    )

    for bar in bars:
        try:
            validate_bar(bar)
        except PriceValidationError as e:
            log.warning("sync.bar_invalid", stock_id=stock_id, error=str(e))
            skipped += 1
            continue

        values = {
            "stock_id": stock_id,
            "date": bar.date,
            "open": bar.open,
            "high": bar.high,
            "low": bar.low,
            "close": bar.close,
            "volume": bar.volume,
            "turnover": bar.turnover,
            "adjust_factor": bar.adjust_factor,
        }
        stmt = sqlite_insert(Price).values(**values)
        stmt = stmt.on_conflict_do_update(
            index_elements=["stock_id", "date"],
            set_={
                "open": stmt.excluded.open,
                "high": stmt.excluded.high,
                "low": stmt.excluded.low,
                "close": stmt.excluded.close,
                "volume": stmt.excluded.volume,
                "turnover": stmt.excluded.turnover,
                "adjust_factor": stmt.excluded.adjust_factor,
            },
        )
        session.exec(stmt)
        if bar.date in existing_dates:
            updated += 1
        else:
            inserted += 1
    session.commit()
    return inserted, updated, skipped


def sync_stock_prices(
    session: Session,
    stock: Stock,
    *,
    full: bool = False,
    lookback_buffer_days: int = 5,
) -> SyncResult:
    """同步单只股票日线（目前仅 A 股 / AKShare）。

    - 增量：从已有最新日期 - buffer 起拉，覆盖可能的复权回填。
    - full=True：全量重拉。
    """
    result = SyncResult(symbol=stock.symbol, market=stock.market, source="akshare")
    if stock.market != "CN":
        result.ok = False
        result.message = f"市场 {stock.market} 暂不支持（Step 1.3 仅 A 股）"
        return result

    start: date | None = None
    if not full:
        latest = _latest_price_date(session, stock.id)  # type: ignore[arg-type]
        if latest is not None:
            start = latest - timedelta(days=lookback_buffer_days)

    try:
        bars = fetch_cn_daily(stock.symbol, start=start)
    except AkShareUnavailable as e:
        result.ok = False
        result.message = str(e)
        log.warning("sync.source_unavailable", symbol=stock.symbol, error=str(e))
        return result

    if not bars:
        result.message = "无新数据"
        return result

    inserted, updated, skipped = _upsert_bars(session, stock.id, bars)  # type: ignore[arg-type]
    result.inserted = inserted
    result.updated = updated
    result.skipped = skipped
    result.message = f"insert={inserted} update={updated} skip={skipped}"
    log.info(
        "sync.stock_done",
        symbol=stock.symbol,
        inserted=inserted,
        updated=updated,
        skipped=skipped,
    )
    return result


def sync_market_prices(session: Session, market: str, *, full: bool = False) -> SyncReport:
    """同步某市场所有已登记股票的行情。"""
    market = market.upper()
    report = SyncReport(market=market)
    stocks = list(session.exec(select(Stock).where(Stock.market == market)).all())
    for stock in stocks:
        report.results.append(sync_stock_prices(session, stock, full=full))

    # 失败 > 5% 告警（设计文档 5.1）
    if report.fail_ratio > 0.05:
        log.error(
            "sync.high_fail_ratio",
            market=market,
            fail_ratio=round(report.fail_ratio, 3),
            failed=[r.symbol for r in report.failed],
        )
    return report
