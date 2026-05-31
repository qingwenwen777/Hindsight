"""管理接口：行情同步触发与状态、数据导出/导入、诊断信息。"""

from __future__ import annotations

import gzip
import shutil
import sqlite3
import tempfile
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlmodel import Session, select

from app.config import settings
from app.core.response import Meta, ok
from app.database import engine, get_session
from app.logging_config import get_logger
from app.models.sync_log import SyncLog
from app.services.data_sync.sync_service import sync_all_prices, sync_market_prices

router = APIRouter(prefix="/admin", tags=["admin"])
log = get_logger(__name__)


@router.post("/provision/industries", summary="回填股票行业标签")
def provision_industries(
    overwrite: bool = Query(False, description="是否覆盖已有行业"),
    session: Session = Depends(get_session),
) -> dict:
    """为已登记股票回填中文行业标签（修复暴露分析"未分类"）。"""
    from app.services.data_sync.provision import backfill_industries

    return ok(backfill_industries(session, overwrite=overwrite))


@router.post("/provision/benchmarks", summary="登记并同步基准指数")
def provision_benchmarks_endpoint(
    market: str | None = Query(None, description="US/CN/HK/JP；空为全部"),
    days: int = Query(400, description="同步最近 N 天"),
    session: Session = Depends(get_session),
) -> dict:
    """登记各市场默认基准指数并同步行情（修复基准对比"无数据"）。"""
    from app.services.data_sync.provision import provision_benchmarks

    markets = [market.upper()] if market else None
    return ok(provision_benchmarks(session, days=days, markets=markets))


@router.post("/sync/prices")
def sync_prices(
    market: str = Query(..., description="市场代码：CN / US / HK / JP"),
    full: bool = Query(False, description="是否全量重拉"),
    session: Session = Depends(get_session),
) -> dict:
    """触发某市场行情同步。"""
    report = sync_market_prices(session, market, full=full)
    return ok(
        {
            "market": report.market,
            "stocks": len(report.results),
            "inserted": report.total_inserted,
            "updated": report.total_updated,
            "failed": [
                {"symbol": r.symbol, "message": r.message} for r in report.failed
            ],
            "results": [
                {
                    "symbol": r.symbol,
                    "ok": r.ok,
                    "inserted": r.inserted,
                    "updated": r.updated,
                    "skipped": r.skipped,
                    "message": r.message,
                }
                for r in report.results
            ],
        }
    )


@router.get("/sync/settings", summary="读取行情同步设置")
def get_sync_settings(session: Session = Depends(get_session)) -> dict:
    """读取"每日自动更新"开关及各市场最近同步时间。"""
    from app.services.data_sync.settings import get_or_create_sync_setting

    setting = get_or_create_sync_setting(session)

    # 附带最近一次任意同步的时间（用于"上次更新"展示）
    last = session.exec(select(SyncLog).order_by(SyncLog.created_at.desc()).limit(1)).first()
    return ok(
        {
            "auto_sync_enabled": setting.auto_sync_enabled,
            "scheduler_running": _scheduler_running(),
            "last_sync_at": last.created_at.isoformat() if last and last.created_at else None,
        }
    )


class SyncSettingsPayload(BaseModel):
    """同步设置更新载荷。"""

    auto_sync_enabled: bool


@router.put("/sync/settings", summary="更新行情同步设置")
def update_sync_settings(
    payload: SyncSettingsPayload, session: Session = Depends(get_session)
) -> dict:
    """开/关"每日自动更新已录入股票行情"。"""
    from app.models.base import utcnow
    from app.services.data_sync.settings import get_or_create_sync_setting

    setting = get_or_create_sync_setting(session)
    setting.auto_sync_enabled = payload.auto_sync_enabled
    setting.updated_at = utcnow()
    session.add(setting)
    session.commit()
    session.refresh(setting)
    log.info("admin.sync_settings_updated", auto_sync_enabled=setting.auto_sync_enabled)
    return ok({"auto_sync_enabled": setting.auto_sync_enabled})


@router.post("/sync/all", summary="立即同步所有已录入股票")
def sync_all(
    full: bool = Query(False, description="是否全量重拉"),
    session: Session = Depends(get_session),
) -> dict:
    """一键同步所有已录入股票的行情（手动触发，不受自动开关影响）。"""
    summary = sync_all_prices(session, full=full)
    return ok(summary)


@router.get("/synced-stocks", summary="本地已拉取的股票及更新时间")
def synced_stocks(session: Session = Depends(get_session)) -> dict:
    """列出本地已登记的股票，附带行情区间与最新更新日期。

    用于设置页"查看本地已拉取股票"。按最新行情日期倒序，
    无行情的股票排在最后（视为尚未拉取/拉取失败）。
    """
    from app.models.stock import Price, Stock
    from sqlalchemy import func

    stocks = list(session.exec(select(Stock)).all())
    out = []
    for st in stocks:
        agg = session.exec(
            select(
                func.max(Price.date),
                func.min(Price.date),
                func.count(Price.date),
            ).where(Price.stock_id == st.id)
        ).first()
        last_date, first_date, bar_count = (agg or (None, None, 0))
        out.append(
            {
                "stock_id": st.id,
                "symbol": st.symbol,
                "name": st.name,
                "market": st.market,
                "currency": st.currency,
                "bars": int(bar_count or 0),
                "first_date": first_date.isoformat() if first_date else None,
                "last_date": last_date.isoformat() if last_date else None,
            }
        )
    # 有行情的在前（按最新日期倒序），无行情的在后
    out.sort(key=lambda r: (r["last_date"] is not None, r["last_date"] or ""), reverse=True)
    return ok(out, meta=Meta(total=len(out)))


# ---- 数据导出 / 导入 ----


def _db_file() -> Path:
    """当前 SQLite 数据库文件路径。"""
    raw = settings.database_url.split("sqlite:///", 1)[-1]
    p = Path(raw)
    return p if p.is_absolute() else (settings.data_dir / "stock.db")


def _make_snapshot(dest_dir: Path) -> Path:
    """用 SQLite 在线 .backup 生成一致性快照并 gzip 压缩，返回 .db.gz 路径。

    WAL 模式下不能直接复制 .db 文件，必须用 backup API 拿一致快照。
    """
    db = _db_file()
    if not db.exists():
        raise HTTPException(status_code=404, detail="数据库文件不存在")

    snapshot = dest_dir / "snapshot.db"
    src = sqlite3.connect(str(db))
    dst = sqlite3.connect(str(snapshot))
    try:
        with dst:
            src.backup(dst)
    finally:
        src.close()
        dst.close()

    gz = dest_dir / "export.db.gz"
    with open(snapshot, "rb") as f_in, gzip.open(gz, "wb") as f_out:
        shutil.copyfileobj(f_in, f_out)
    snapshot.unlink(missing_ok=True)
    return gz


@router.get("/data/export", summary="导出全部数据（SQLite 快照）")
def export_data() -> FileResponse:
    """导出整库为 gzip 压缩的一致性快照，供用户备份到本地/网盘。"""
    tmp_dir = Path(tempfile.mkdtemp(prefix="tradeai_export_"))
    gz = _make_snapshot(tmp_dir)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"hindsight_backup_{ts}.db.gz"
    log.info("admin.data_export", size=gz.stat().st_size)
    return FileResponse(
        path=str(gz),
        media_type="application/gzip",
        filename=filename,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/data/import", summary="导入数据（覆盖当前库，先自动备份）")
async def import_data(file: UploadFile = File(...)) -> dict:
    """用上传的备份文件覆盖当前数据库。

    安全措施：
    1. 先校验上传文件是合法 SQLite（含本应用关键表），不合法直接拒绝。
    2. 覆盖前把现有库另存为 .pre-import 备份，失败可回滚。
    3. 释放连接池后再替换文件，避免句柄占用。
    """
    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=422, detail="上传文件为空")

    # 解压（支持 .db.gz 或裸 .db）
    data = raw
    if file.filename and file.filename.endswith(".gz"):
        try:
            data = gzip.decompress(raw)
        except OSError as e:
            raise HTTPException(status_code=422, detail=f"gzip 解压失败：{e}") from e
    elif raw[:2] == b"\x1f\x8b":  # gzip magic
        try:
            data = gzip.decompress(raw)
        except OSError:
            data = raw

    # 写到临时文件并校验是合法 SQLite + 含关键表
    tmp_dir = Path(tempfile.mkdtemp(prefix="tradeai_import_"))
    candidate = tmp_dir / "candidate.db"
    candidate.write_bytes(data)
    try:
        con = sqlite3.connect(str(candidate))
        try:
            names = {
                r[0]
                for r in con.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }
        finally:
            con.close()
    except sqlite3.DatabaseError as e:
        raise HTTPException(status_code=422, detail=f"不是有效的数据库文件：{e}") from e

    required = {"stocks", "transactions", "journals"}
    if not required.issubset(names):
        missing = required - names
        raise HTTPException(
            status_code=422,
            detail=f"备份文件缺少关键表：{', '.join(sorted(missing))}，可能不是本应用的备份",
        )

    db = _db_file()
    db.parent.mkdir(parents=True, exist_ok=True)

    # 释放连接池，确保无句柄占用
    engine.dispose()

    # 覆盖前备份现有库（含 wal/shm 一并清理，避免与新库不一致）
    if db.exists():
        backup = db.with_suffix(db.suffix + ".pre-import")
        shutil.copy2(db, backup)
    for ext in ("-wal", "-shm"):
        side = Path(str(db) + ext)
        if side.exists():
            side.unlink()

    shutil.copy2(candidate, db)
    log.info("admin.data_import", size=len(data), tables=len(names))
    return ok({"ok": True, "tables": sorted(names)})


# ---- 诊断信息 ----


@router.get("/diagnostics", summary="诊断信息汇总")
def diagnostics(session: Session = Depends(get_session)) -> dict:
    """汇总诊断信息：版本、数据库大小、各表行数、同步状态。用于排障。"""
    from app.models.stock import Price, Stock
    from app.models.transaction import Transaction
    from sqlalchemy import func

    db = _db_file()
    db_size = db.stat().st_size if db.exists() else 0

    counts = {
        "stocks": session.exec(select(func.count(Stock.id))).one(),
        "transactions": session.exec(select(func.count(Transaction.id))).one(),
        "prices": session.exec(select(func.count(Price.date))).one(),
        "sync_logs": session.exec(select(func.count(SyncLog.id))).one(),
    }

    last = session.exec(select(SyncLog).order_by(SyncLog.created_at.desc()).limit(1)).first()
    return ok(
        {
            "app": settings.app_name,
            "db_path": str(db),
            "db_size_bytes": db_size,
            "scheduler_running": settings.enable_scheduler,
            "counts": counts,
            "last_sync_at": last.created_at.isoformat() if last and last.created_at else None,
            "generated_at": datetime.now().isoformat(),
        }
    )


def _scheduler_running() -> bool:
    """调度器是否已启用（环境变量 ENABLE_SCHEDULER）。"""
    from app.config import settings

    return settings.enable_scheduler


@router.get("/sync/logs", summary="同步日志")
def sync_logs(
    limit: int = Query(50, le=500),
    market: str | None = Query(None),
    session: Session = Depends(get_session),
) -> dict:
    """查询最近的同步日志。"""
    stmt = select(SyncLog)
    if market:
        stmt = stmt.where(SyncLog.market == market.upper())
    stmt = stmt.order_by(SyncLog.created_at.desc()).limit(limit)
    rows = list(session.exec(stmt).all())
    data = [
        {
            "id": r.id,
            "market": r.market,
            "symbol": r.symbol,
            "source": r.source,
            "ok": r.ok,
            "inserted": r.inserted,
            "updated": r.updated,
            "skipped": r.skipped,
            "message": r.message,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]
    return ok(data, meta=Meta(total=len(data)))


@router.get("/sync/status", summary="同步状态汇总")
def sync_status(session: Session = Depends(get_session)) -> dict:
    """各市场最近一次同步状态。"""
    out: dict[str, dict] = {}
    for market in ("CN", "US", "HK", "JP"):
        last = session.exec(
            select(SyncLog)
            .where(SyncLog.market == market)
            .order_by(SyncLog.created_at.desc())
            .limit(1)
        ).first()
        out[market] = (
            {
                "ok": last.ok,
                "source": last.source,
                "message": last.message,
                "at": last.created_at.isoformat() if last.created_at else None,
            }
            if last
            else None
        )
    return ok(out)


@router.post("/sync/fx", summary="同步汇率")
def sync_fx(
    days: int = Query(30, description="拉取最近 N 天"),
    session: Session = Depends(get_session),
) -> dict:
    """通过 yfinance 拉取汇率并写入 fx_rates。"""
    from app.services.data_sync.fx_client import sync_fx_rates
    from app.services.data_sync.yfinance_client import YFinanceUnavailable

    try:
        summary = sync_fx_rates(session, days=days)
    except YFinanceUnavailable as e:
        return ok({"ok": False, "message": str(e)})
    return ok(summary)


@router.post("/sync/financials", summary="同步财务/估值指标")
def sync_financials(
    market: str | None = Query(None, description="限定市场；空为全部已登记股票"),
    session: Session = Depends(get_session),
) -> dict:
    """拉取财务/估值指标并 UPSERT 到 financials。"""
    from sqlalchemy.dialects.sqlite import insert as sqlite_insert

    from app.models.financials import Financial
    from app.models.stock import Stock
    from app.services.data_sync.financials_client import fetch_financials
    from app.services.data_sync.yfinance_client import YFinanceUnavailable

    stmt = select(Stock)
    if market:
        stmt = stmt.where(Stock.market == market.upper())
    stocks = list(session.exec(stmt).all())

    updated = 0
    failed: list[str] = []
    for stock in stocks:
        try:
            data = fetch_financials(stock.symbol, stock.market)
        except YFinanceUnavailable as e:
            return ok({"ok": False, "message": str(e)})
        if not data:
            failed.append(stock.symbol)
            continue
        values = {"stock_id": stock.id, **data}
        ins = sqlite_insert(Financial).values(**values)
        ins = ins.on_conflict_do_update(
            index_elements=["stock_id", "as_of"],
            set_={k: ins.excluded[k] for k in data if k != "as_of"},
        )
        session.exec(ins)
        updated += 1
    session.commit()
    return ok({"updated": updated, "failed": failed, "total": len(stocks)})


def _seed_universe_task(market: str | None, do_sync: bool) -> None:
    """后台任务：扩充股票池。"""
    try:
        from scripts.seed_universe import seed_universe

        markets = [market.upper()] if market else ["US", "HK", "JP", "CN"]
        seed_universe(markets, do_sync=do_sync)
    except Exception as e:  # noqa: BLE001
        log.warning("admin.seed_universe_failed", market=market, error=str(e))


@router.post("/seed-universe", summary="扩充股票池（成分股）")
def seed_universe_endpoint(
    background_tasks: BackgroundTasks,
    market: str | None = Query(None, description="US/CN/HK/JP；空为全部"),
    sync: bool = Query(True, description="是否同步行情/财务"),
) -> dict:
    """后台批量登记各市场精选成分股并同步。"""
    background_tasks.add_task(_seed_universe_task, market, sync)
    return ok({"status": "seeding", "market": market or "ALL"})


@router.get("/universe-status", summary="股票池数据完备度")
def universe_status(session: Session = Depends(get_session)) -> dict:
    """各市场：已登记 / 有行情 / 有财务 计数。"""
    from app.models.financials import Financial
    from app.models.stock import Price, Stock

    out: dict[str, dict] = {}
    for market in ("US", "CN", "HK", "JP"):
        stocks = list(session.exec(select(Stock).where(Stock.market == market)).all())
        registered = len(stocks)
        with_price = 0
        with_fin = 0
        for st in stocks:
            if session.exec(select(Price.date).where(Price.stock_id == st.id).limit(1)).first():
                with_price += 1
            if session.exec(select(Financial.id).where(Financial.stock_id == st.id).limit(1)).first():
                with_fin += 1
        out[market] = {
            "registered": registered,
            "with_price": with_price,
            "with_financials": with_fin,
        }
    return ok(out)
