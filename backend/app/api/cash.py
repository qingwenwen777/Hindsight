"""现金账户与现金流 API。"""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlmodel import Session, select

from app.core.money import D, to_db_str
from app.core.response import Meta, ok
from app.database import get_session
from app.models.cash import CashAccount, CashFlow
from app.services.analysis import cash as cash_service

router = APIRouter(prefix="/portfolio", tags=["cash"])


class AccountCreate(BaseModel):
    name: str
    broker: str | None = None
    currency: str
    notes: str | None = None


class AccountUpdate(BaseModel):
    name: str | None = None
    broker: str | None = None
    currency: str | None = None
    notes: str | None = None


class CashFlowCreate(BaseModel):
    account_id: int
    flow_date: date | None = None
    type: str  # DEPOSIT/WITHDRAW/DIVIDEND/INTEREST/...
    amount: str  # 正入负出
    currency: str | None = None
    notes: str | None = None


@router.post("/accounts", summary="创建现金账户")
def create_account(payload: AccountCreate, session: Session = Depends(get_session)) -> dict:
    acc = CashAccount(
        name=payload.name,
        broker=payload.broker,
        currency=payload.currency.upper(),
        notes=payload.notes,
    )
    session.add(acc)
    session.commit()
    session.refresh(acc)
    return ok(acc)


@router.patch("/accounts/{account_id}", summary="修改现金账户")
def update_account(
    account_id: int, payload: AccountUpdate, session: Session = Depends(get_session)
) -> dict:
    acc = session.get(CashAccount, account_id)
    if not acc:
        raise HTTPException(status_code=404, detail="账户不存在")
    if payload.name is not None:
        acc.name = payload.name
    if payload.broker is not None:
        acc.broker = payload.broker
    if payload.currency is not None:
        acc.currency = payload.currency.upper()
    if payload.notes is not None:
        acc.notes = payload.notes
    session.add(acc)
    session.commit()
    session.refresh(acc)
    return ok(acc)


@router.delete("/accounts/{account_id}", summary="删除现金账户")
def delete_account(account_id: int, session: Session = Depends(get_session)) -> dict:
    """删除账户。若仍有非交易类现金流则一并清理；关联交易的流水阻止删除以防丢账。"""
    acc = session.get(CashAccount, account_id)
    if not acc:
        raise HTTPException(status_code=404, detail="账户不存在")
    # 是否存在交易产生的现金流（related_tx_id 非空）
    linked = session.exec(
        select(CashFlow).where(
            CashFlow.account_id == account_id, CashFlow.related_tx_id.is_not(None)
        )
    ).first()
    if linked:
        raise HTTPException(
            status_code=409, detail="该账户有交易关联的现金流，请先处理相关交易后再删除"
        )
    # 清理手工现金流
    for cf in session.exec(select(CashFlow).where(CashFlow.account_id == account_id)).all():
        session.delete(cf)
    session.flush()  # 先落库删除子记录，再删父账户，避免外键约束失败
    session.delete(acc)
    session.commit()
    return ok({"deleted": account_id})


@router.get("/accounts", summary="账户列表（含余额）")
def list_accounts(session: Session = Depends(get_session)) -> dict:
    accounts = list(session.exec(select(CashAccount)).all())
    data = [
        {
            "id": a.id,
            "name": a.name,
            "broker": a.broker,
            "currency": a.currency,
            "balance": to_db_str(cash_service.account_balance(session, a.id)),  # type: ignore[arg-type]
        }
        for a in accounts
    ]
    return ok(data, meta=Meta(total=len(data)))


@router.post("/cash-flows", summary="新增现金流（入金/出金/分红/利息）")
def create_cash_flow(payload: CashFlowCreate, session: Session = Depends(get_session)) -> dict:
    acc = session.get(CashAccount, payload.account_id)
    if not acc:
        raise HTTPException(status_code=404, detail="账户不存在")
    cf = cash_service.add_cash_flow(
        session,
        payload.account_id,
        payload.flow_date or date.today(),
        payload.type.upper(),
        D(payload.amount),
        (payload.currency or acc.currency).upper(),
        notes=payload.notes,
    )
    return ok(
        {
            "id": cf.id,
            "account_id": cf.account_id,
            "type": cf.type,
            "amount": to_db_str(cf.amount),
            "balance": to_db_str(cash_service.account_balance(session, payload.account_id)),
        }
    )


@router.get("/cash-flows", summary="现金流列表")
def list_cash_flows(
    account_id: int | None = Query(None),
    session: Session = Depends(get_session),
) -> dict:
    stmt = select(CashFlow)
    if account_id:
        stmt = stmt.where(CashFlow.account_id == account_id)
    stmt = stmt.order_by(CashFlow.flow_date.desc(), CashFlow.id.desc())
    rows = list(session.exec(stmt).all())
    data = [
        {
            "id": r.id,
            "account_id": r.account_id,
            "flow_date": r.flow_date.isoformat(),
            "type": r.type,
            "amount": to_db_str(r.amount),
            "currency": r.currency,
            "related_tx_id": r.related_tx_id,
            "notes": r.notes,
        }
        for r in rows
    ]
    return ok(data, meta=Meta(total=len(data)))
