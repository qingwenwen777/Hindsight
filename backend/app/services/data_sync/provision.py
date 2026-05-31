"""数据补全：行业回填 + 基准指数登记与同步。

解决两个常见空数据问题：
1. 暴露分析"行业 100% 未分类"——股票 industry 列为空。
2. 基准对比"未找到基准行情"——基准指数（^GSPC 等）未登记或无行情。
"""

from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlmodel import Session, select

from app.logging_config import get_logger
from app.models.stock import Price, Stock
from app.services.data_sync.base import PriceValidationError, validate_bar
from app.services.data_sync.industry_map import BENCHMARKS, lookup_industry

log = get_logger(__name__)


def backfill_industries(session: Session, *, overwrite: bool = False) -> dict:
    """为已登记股票回填中文行业标签。

    overwrite=False：只填补当前为空的；True：用映射表覆盖所有命中项。
    映射表未命中的股票尝试用 yfinance 的 sector（英文）兜底。
    """
    stocks = list(session.exec(select(Stock)).all())
    updated = 0
    miss: list[str] = []
    for st in stocks:
        if st.industry and not overwrite:
            continue
        ind = lookup_industry(st.symbol, st.market)
        if ind is None:
            ind = _yf_sector(st.symbol, st.market)
        if ind:
            st.industry = ind
            session.add(st)
            updated += 1
        else:
            miss.append(f"{st.market}:{st.symbol}")
    session.commit()
    return {"updated": updated, "missed": miss, "total": len(stocks)}


def _yf_sector(symbol: str, market: str) -> str | None:
    """yfinance 兜底取 sector（英文）。失败返回 None。"""
    try:
        import yfinance as yf  # noqa: PLC0415

        from app.services.data_sync.yfinance_client import to_yf_symbol

        info = yf.Ticker(to_yf_symbol(symbol, market)).info
        if isinstance(info, dict):
            return info.get("sector") or info.get("industry") or None
    except Exception as e:  # noqa: BLE001
        log.warning("provision.yf_sector_failed", symbol=symbol, error=str(e))
    return None


def _upsert_prices(session: Session, stock_id: int, bars) -> int:  # noqa: ANN001
    """UPSERT 基准指数日线，返回写入条数。"""
    count = 0
    for bar in bars:
        try:
            validate_bar(bar)
        except PriceValidationError:
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
            },
        )
        session.exec(stmt)
        count += 1
    session.commit()
    return count


def provision_benchmarks(session: Session, *, days: int = 400, markets: list[str] | None = None) -> dict:
    """登记各市场默认基准指数并同步行情。

    基准指数（^GSPC/^HSI/^N225/000300）作为 is_etf 标记的 Stock 登记，
    用专用 yfinance ticker 抓取日线，供基准对比 API 对齐组合收益。
    """
    from app.services.data_sync.yfinance_client import (
        YFinanceUnavailable,
        fetch_yf_daily_by_ticker,
    )

    target = markets or list(BENCHMARKS.keys())
    start = date.today() - timedelta(days=days)
    out: dict[str, dict] = {}
    for market in target:
        spec = BENCHMARKS.get(market.upper())
        if not spec:
            continue
        stock = session.exec(
            select(Stock).where(
                Stock.symbol == spec["symbol"], Stock.market == market.upper()
            )
        ).first()
        if not stock:
            stock = Stock(
                symbol=spec["symbol"],
                market=market.upper(),
                name=spec["name"],
                currency=spec["currency"],
                industry="指数",
                is_etf=True,
            )
            session.add(stock)
            session.commit()
            session.refresh(stock)
        try:
            bars = fetch_yf_daily_by_ticker(spec["yf"], start=start)
        except YFinanceUnavailable as e:
            out[market] = {"ok": False, "message": str(e)}
            continue
        written = _upsert_prices(session, stock.id, bars)  # type: ignore[arg-type]
        out[market] = {
            "ok": True,
            "symbol": spec["symbol"],
            "name": spec["name"],
            "written": written,
        }
        log.info("provision.benchmark", market=market, symbol=spec["symbol"], written=written)
    return out
