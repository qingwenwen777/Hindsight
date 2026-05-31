"""现金账户余额与现金流服务。"""

from __future__ import annotations

from decimal import Decimal

from sqlmodel import Session, select

from app.core.money import D
from app.models.cash import CashAccount, CashFlow

ZERO = Decimal("0")


def account_balance(session: Session, account_id: int) -> Decimal:
    """账户余额（以账户币种计）。

    现金流的 currency 正常应与账户币种一致；历史/异常数据中可能混入其它币种。
    为避免跨币种直接相加（把 USD 与 JPY 数值当同币种求和），这里：
      - 与账户同币种的流水直接累加；
      - 不同币种的流水按当天汇率换算到账户币种后并入（缺汇率则跳过，不污染余额）。
    """
    acc = session.get(CashAccount, account_id)
    acc_ccy = acc.currency.upper() if acc and acc.currency else None

    flows = session.exec(
        select(CashFlow.amount, CashFlow.currency).where(CashFlow.account_id == account_id)
    ).all()
    total = ZERO
    for amount, ccy in flows:
        amt = D(amount)
        fccy = (ccy or acc_ccy or "").upper()
        if acc_ccy is None or fccy == acc_ccy:
            total += amt
            continue
        # 跨币种：换算到账户币种
        from datetime import date

        from app.core.currency import FxRateUnavailable, get_fx_quote

        try:
            q = get_fx_quote(session, fccy, acc_ccy, date.today())
            total += amt * q.rate
        except FxRateUnavailable:
            continue  # 缺汇率：跳过，避免把异币种原值并入
    return total


def cash_summary(session: Session, target_currency: str = "JPY") -> dict:
    """现金总览：按币种汇总余额 + 折算到目标币种的总额（按当天汇率）。

    返回：
      {
        "by_currency": [{"currency", "balance", "converted", "rate", "estimated"}],
        "total": {"currency", "amount", "estimated"},
      }
    总额折算时，任一腿用了回退/估算汇率即标记 estimated=True。
    """
    from datetime import date

    from app.core.currency import FxRateUnavailable, get_fx_quote

    target_currency = target_currency.upper()
    accounts = list(session.exec(select(CashAccount)).all())

    # 按币种聚合余额
    per_ccy: dict[str, Decimal] = {}
    for acc in accounts:
        bal = account_balance(session, acc.id)
        per_ccy[acc.currency] = per_ccy.get(acc.currency, ZERO) + bal

    today = date.today()
    by_currency: list[dict] = []
    total = ZERO
    total_estimated = False

    for ccy in sorted(per_ccy.keys()):
        bal = per_ccy[ccy]
        converted: Decimal | None = None
        rate: Decimal | None = None
        estimated = False
        if ccy == target_currency:
            converted = bal
            rate = D("1")
        else:
            try:
                quote = get_fx_quote(session, ccy, target_currency, today)
                rate = quote.rate
                converted = bal * quote.rate
                estimated = quote.is_estimated
            except FxRateUnavailable:
                converted = None
                estimated = True
        if converted is not None:
            total += converted
        else:
            total_estimated = True
        if estimated:
            total_estimated = True
        by_currency.append(
            {
                "currency": ccy,
                "balance": bal,
                "converted": converted,
                "rate": rate,
                "estimated": estimated,
            }
        )

    return {
        "by_currency": by_currency,
        "total": {"currency": target_currency, "amount": total, "estimated": total_estimated},
    }


def add_cash_flow(
    session: Session,
    account_id: int,
    flow_date,  # noqa: ANN001
    flow_type: str,
    amount: Decimal | str,
    currency: str,
    *,
    related_tx_id: int | None = None,
    notes: str | None = None,
    commit: bool = True,
) -> CashFlow:
    """新增一条现金流。"""
    cf = CashFlow(
        account_id=account_id,
        flow_date=flow_date,
        type=flow_type,
        amount=D(amount),
        currency=currency.upper(),
        related_tx_id=related_tx_id,
        notes=notes,
    )
    session.add(cf)
    if commit:
        session.commit()
        session.refresh(cf)
    return cf


def generate_trade_cash_flows(
    session: Session,
    account_id: int,
    tx_id: int,
    side: str,
    amount: Decimal,
    fees: Decimal,
    currency: str,
    flow_date,  # noqa: ANN001
    *,
    commit: bool = True,
) -> list[CashFlow]:
    """交易自动产生现金流。

    买入：现金流出 = -(成交额 + 费用)，记为 TRADE_BUY。
    卖出：现金流入 = +(成交额 - 费用)，记为 TRADE_SELL。
    （费用已并入主现金流，不再单列 FEE，避免重复计账。）
    """
    side = side.upper()
    if side == "BUY":
        net = -(amount + fees)
        flow_type = "TRADE_BUY"
    else:
        net = amount - fees
        flow_type = "TRADE_SELL"
    cf = add_cash_flow(
        session,
        account_id,
        flow_date,
        flow_type,
        net,
        currency,
        related_tx_id=tx_id,
        commit=commit,
    )
    return [cf]
