"""行情同步服务 —— 增量同步 + 校验 + UPSERT。"""

from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlmodel import Session, select

from app.logging_config import get_logger
from app.models.stock import Price, Stock
from app.models.sync_log import SyncLog
from app.services.data_sync.akshare_client import AkShareUnavailable, fetch_cn_daily
from app.services.data_sync.yfinance_client import YFinanceUnavailable, fetch_yf_daily
from app.services.data_sync.base import (
    PriceBar,
    PriceValidationError,
    SyncReport,
    SyncResult,
    validate_bar,
)

log = get_logger(__name__)

# 各市场容错优先级链路（设计文档 5.1）。
# 每个 source 是 (名称, 拉取函数)；按顺序尝试，成功即止。
_FETCHERS: dict[str, list[str]] = {
    "CN": ["akshare", "yfinance"],
    "HK": ["akshare", "yfinance"],
    "US": ["yfinance", "akshare"],
    "JP": ["yfinance"],
}


def _fetch_via_source(
    source: str, stock: Stock, start: date | None
) -> list[PriceBar]:
    """按 source 名称分派到对应客户端。"""
    if source == "akshare":
        if stock.market == "CN":
            return fetch_cn_daily(stock.symbol, start=start)
        # AKShare 也能拉港股/美股，但接口不同；当前仅 A 股走 akshare，其余抛不可用触发回退
        raise AkShareUnavailable(f"akshare 暂未实现 {stock.market} 拉取，回退下一源")
    if source == "yfinance":
        return fetch_yf_daily(stock.symbol, stock.market, start=start)
    raise ValueError(f"未知数据源：{source}")


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
    # 写入后失效 parquet 缓存
    try:
        from app.services.analysis.price_cache import invalidate_price_cache

        invalidate_price_cache(stock_id)
    except Exception:  # noqa: BLE001  缓存失效失败不影响同步
        pass
    return inserted, updated, skipped


def sync_stock_prices(
    session: Session,
    stock: Stock,
    *,
    full: bool = False,
    lookback_buffer_days: int = 5,
    write_log: bool = True,
) -> SyncResult:
    """同步单只股票日线，按市场容错优先级依次尝试数据源。

    - 增量：从已有最新日期 - buffer 起拉，覆盖可能的复权回填。
    - full=True：全量重拉。
    - 按 _FETCHERS[market] 的顺序尝试，成功即止；全部失败标记失败。
    """
    result = SyncResult(symbol=stock.symbol, market=stock.market)
    sources = _FETCHERS.get(stock.market.upper())
    if not sources:
        result.ok = False
        result.message = f"市场 {stock.market} 无可用数据源"
        if write_log:
            _write_sync_log(session, result)
        return result

    start: date | None = None
    if not full:
        latest = _latest_price_date(session, stock.id)  # type: ignore[arg-type]
        if latest is not None:
            start = latest - timedelta(days=lookback_buffer_days)

    bars: list[PriceBar] | None = None
    errors: list[str] = []
    for source in sources:
        try:
            bars = _fetch_via_source(source, stock, start)
            result.source = source
            break
        except (AkShareUnavailable, YFinanceUnavailable) as e:
            errors.append(f"{source}: {e}")
            log.warning("sync.source_failed", symbol=stock.symbol, source=source, error=str(e))
            continue

    if bars is None:
        result.ok = False
        result.message = "所有数据源失败：" + " | ".join(errors)
        log.error("sync.all_sources_failed", symbol=stock.symbol, errors=errors)
        if write_log:
            _write_sync_log(session, result)
        return result

    if not bars:
        result.message = "无新数据"
        if write_log:
            _write_sync_log(session, result)
        return result

    inserted, updated, skipped = _upsert_bars(session, stock.id, bars)  # type: ignore[arg-type]
    result.inserted = inserted
    result.updated = updated
    result.skipped = skipped
    result.message = f"insert={inserted} update={updated} skip={skipped}"
    log.info(
        "sync.stock_done",
        symbol=stock.symbol,
        source=result.source,
        inserted=inserted,
        updated=updated,
        skipped=skipped,
    )
    if write_log:
        _write_sync_log(session, result)
    return result


def _write_sync_log(session: Session, result: SyncResult) -> None:
    """把同步结果写入 sync_logs 表。"""
    session.add(
        SyncLog(
            market=result.market,
            symbol=result.symbol,
            source=result.source or None,
            ok=result.ok,
            inserted=result.inserted,
            updated=result.updated,
            skipped=result.skipped,
            message=result.message,
        )
    )
    session.commit()


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
