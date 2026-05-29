"""交易录入 API —— 强制决策日志 + 单事务写入。"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field, field_validator
from sqlmodel import Session, select

from app.core.fees import calculate_fees
from app.core.money import D, to_db_str
from app.core.response import Meta, ok
from app.database import get_session
from app.models.base import utcnow
from app.models.journal import Journal
from app.models.stock import Stock
from app.models.transaction import Transaction

router = APIRouter(prefix="/transactions", tags=["transactions"])


class JournalIn(BaseModel):
    """录入交易时强制附带的决策日志（设计文档 F4.2）。"""

    decision_type: str
    thesis_category: str | None = None
    expected_horizon: str | None = None
    target_price: str | None = None
    stop_loss_price: str | None = None
    exit_condition: str | None = None
    confidence: int | None = Field(default=None, ge=1, le=5)
    emotion: str | None = None
    thesis: str = Field(..., min_length=1, description="投资逻辑，必填")
    risks: str | None = None
    tags: list[str] | None = None


class TransactionIn(BaseModel):
    """交易录入入参。"""

    stock_id: int
    type: str  # BUY / SELL
    trade_date: date
    quantity: str
    price: str
    currency: str
    fx_rate_to_jpy: str | None = None
    commission: str | None = None
    tax: str | None = None
    other_fees: str | None = None
    broker: str | None = None
    account_id: int | None = None  # 关联现金账户（提供则自动产生现金流）
    notes: str | None = None
    # 强制日志（缺失则 422）
    journal: JournalIn

    @field_validator("type")
    @classmethod
    def _check_type(cls, v: str) -> str:
        if v.upper() not in ("BUY", "SELL"):
            raise ValueError("type 必须是 BUY 或 SELL")
        return v.upper()


def _serialize_tx(tx: Transaction) -> dict:
    return {
        "id": tx.id,
        "stock_id": tx.stock_id,
        "type": tx.type,
        "trade_date": tx.trade_date.isoformat(),
        "quantity": to_db_str(tx.quantity),
        "price": to_db_str(tx.price),
        "currency": tx.currency,
        "commission": to_db_str(tx.commission),
        "tax": to_db_str(tx.tax),
        "other_fees": to_db_str(tx.other_fees),
        "journal_id": tx.journal_id,
        "is_imported": tx.is_imported,
        "notes": tx.notes,
    }


@router.post("", summary="录入交易（强制日志）")
def create_transaction(payload: TransactionIn, session: Session = Depends(get_session)) -> dict:
    """在单个数据库事务里写 journal(锁定) + transaction(关联 journal_id)。

    - 缺少日志必填字段（thesis）→ 由 pydantic 触发 422。
    - 费用缺省时用手续费引擎自动计算。
    - 失效持仓缓存（Step 1.5 接入缓存后在此调用）。
    """
    stock = session.get(Stock, payload.stock_id)
    if not stock:
        raise HTTPException(status_code=404, detail="股票不存在")

    quantity = D(payload.quantity)
    price = D(payload.price)
    amount = quantity * price

    # 费用：显式传入优先，否则引擎计算
    if payload.commission is None and payload.tax is None and payload.other_fees is None:
        fees = calculate_fees(
            stock.market,
            payload.type,
            amount,
            quantity,
            broker=payload.broker,
            trade_date=payload.trade_date,
            session=session,
        ).quantized()
        commission, tax, other_fees = fees.commission, fees.tax, fees.other_fees
    else:
        commission = D(payload.commission or "0")
        tax = D(payload.tax or "0")
        other_fees = D(payload.other_fees or "0")

    j = payload.journal
    # 1. 写日志并立即锁定
    journal = Journal(
        stock_id=payload.stock_id,
        decision_type=j.decision_type,
        thesis_category=j.thesis_category,
        expected_horizon=j.expected_horizon,
        target_price=D(j.target_price) if j.target_price else None,
        stop_loss_price=D(j.stop_loss_price) if j.stop_loss_price else None,
        exit_condition=j.exit_condition,
        confidence=j.confidence,
        emotion=j.emotion,
        thesis=j.thesis,
        risks=j.risks,
        tags=j.tags,
        is_locked=True,
        locked_at=utcnow(),
    )
    session.add(journal)
    session.flush()  # 拿到 journal.id

    # 2. 写交易，关联 journal_id
    tx = Transaction(
        stock_id=payload.stock_id,
        type=payload.type,
        trade_date=payload.trade_date,
        quantity=quantity,
        price=price,
        currency=payload.currency.upper(),
        fx_rate_to_jpy=D(payload.fx_rate_to_jpy) if payload.fx_rate_to_jpy else None,
        commission=commission,
        tax=tax,
        other_fees=other_fees,
        journal_id=journal.id,
        notes=payload.notes,
    )
    session.add(tx)

    # 3. 失效持仓缓存（Step 6 接入缓存后启用）
    from app.services.analysis import pnl as pnl_service

    pnl_service.invalidate_holdings_cache(payload.stock_id)

    # 4. 若指定现金账户，自动产生交易现金流
    if payload.account_id is not None:
        session.flush()  # 拿到 tx.id
        from app.services.analysis import cash as cash_service

        amount = quantity * price
        total_fees = commission + tax + other_fees
        cash_service.generate_trade_cash_flows(
            session,
            payload.account_id,
            tx.id,  # type: ignore[arg-type]
            payload.type,
            amount,
            total_fees,
            payload.currency.upper(),
            payload.trade_date,
            commit=False,
        )

    session.commit()
    session.refresh(tx)

    return ok(
        {
            "transaction": _serialize_tx(tx),
            "journal_id": journal.id,
            "fees": {
                "commission": to_db_str(commission),
                "tax": to_db_str(tax),
                "other_fees": to_db_str(other_fees),
            },
        },
        message="已记录",
    )


@router.get("", summary="交易列表")
def list_transactions(
    stock_id: int | None = Query(None),
    start: date | None = Query(None),
    end: date | None = Query(None),
    type: str | None = Query(None),
    session: Session = Depends(get_session),
) -> dict:
    """查询交易流水。"""
    stmt = select(Transaction)
    if stock_id:
        stmt = stmt.where(Transaction.stock_id == stock_id)
    if start:
        stmt = stmt.where(Transaction.trade_date >= start)
    if end:
        stmt = stmt.where(Transaction.trade_date <= end)
    if type:
        stmt = stmt.where(Transaction.type == type.upper())
    stmt = stmt.order_by(Transaction.trade_date.desc(), Transaction.id.desc())
    rows = list(session.exec(stmt).all())
    return ok([_serialize_tx(t) for t in rows], meta=Meta(total=len(rows)))


@router.get("/{tx_id}", summary="交易详情")
def get_transaction(tx_id: int, session: Session = Depends(get_session)) -> dict:
    tx = session.get(Transaction, tx_id)
    if not tx:
        raise HTTPException(status_code=404, detail="交易不存在")
    return ok(_serialize_tx(tx))


@router.delete("/{tx_id}", summary="删除交易（仅未锁定的占位记录）")
def delete_transaction(tx_id: int, session: Session = Depends(get_session)) -> dict:
    """仅允许删除导入的占位记录（其 journal 未锁定）。"""
    tx = session.get(Transaction, tx_id)
    if not tx:
        raise HTTPException(status_code=404, detail="交易不存在")
    if tx.journal_id:
        journal = session.get(Journal, tx.journal_id)
        if journal and journal.is_locked and not journal.is_imported:
            raise HTTPException(status_code=403, detail="已锁定日志的交易不可删除")
    session.delete(tx)
    from app.services.analysis import pnl as pnl_service

    pnl_service.invalidate_holdings_cache(tx.stock_id)
    session.commit()
    return ok({"deleted": tx_id})


@router.post("/import/preview", summary="CSV 导入预览")
async def import_preview(
    file: UploadFile = File(...),
    broker: str | None = None,
) -> dict:
    """上传 CSV，自动检测格式并返回解析预览（不写库）。"""
    from app.services.import_csv import parse_csv

    raw = await file.read()
    try:
        content = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        content = raw.decode("gbk", errors="replace")
    preview = parse_csv(content, broker=broker)
    return ok(
        {
            "broker": preview.broker,
            "columns": preview.columns,
            "total": len(preview.rows),
            "valid": len(preview.valid_rows),
            "invalid": len(preview.invalid_rows),
            "rows": [
                {
                    "symbol": r.symbol,
                    "market": r.market,
                    "type": r.type,
                    "trade_date": r.trade_date,
                    "quantity": r.quantity,
                    "price": r.price,
                    "currency": r.currency,
                    "commission": r.commission,
                    "tax": r.tax,
                    "other_fees": r.other_fees,
                    "error": r.error,
                }
                for r in preview.rows
            ],
        }
    )


@router.post("/import", summary="CSV 导入提交")
async def import_commit(
    file: UploadFile = File(...),
    broker: str | None = None,
    session: Session = Depends(get_session),
) -> dict:
    """上传 CSV 并批量写入有效行（每行建占位 journal，is_imported=true）。"""
    from app.services.import_csv import commit_import, parse_csv

    raw = await file.read()
    try:
        content = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        content = raw.decode("gbk", errors="replace")
    preview = parse_csv(content, broker=broker)
    result = commit_import(session, preview)
    return ok(result, message="导入完成")
