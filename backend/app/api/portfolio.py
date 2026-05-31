"""组合接口：持仓、汇总。"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session

from app.core.currency import FxRateUnavailable, get_fx_quote
from app.core.money import quantize_money, to_db_str
from app.core.response import Meta, ok
from app.database import get_session
from app.services.analysis import pnl as pnl_service

router = APIRouter(prefix="/portfolio", tags=["portfolio"])

ZERO = Decimal("0")


@router.get("/holdings", summary="持仓列表")
def get_holdings(session: Session = Depends(get_session)) -> dict:
    """返回当前所有持仓（含 FIFO 成本、市值、浮盈、参考均价）。"""
    items = pnl_service.compute_all_holdings(session)
    data = []
    for ph in items:
        h = ph.holding
        mv = h.market_value(ph.last_price)
        upnl = h.unrealized_pnl(ph.last_price)
        data.append(
            {
                "stock_id": ph.stock.id,
                "symbol": ph.stock.symbol,
                "market": ph.stock.market,
                "name": ph.stock.name,
                "currency": ph.stock.currency,
                "shares": to_db_str(h.shares),
                "avg_cost": to_db_str(quantize_money(h.avg_cost, Decimal("0.0001"))),
                "cost_basis": to_db_str(quantize_money(h.cost_basis)),
                "last_price": to_db_str(ph.last_price),
                "market_value": to_db_str(quantize_money(mv)) if mv is not None else None,
                "unrealized_pnl": to_db_str(quantize_money(upnl)) if upnl is not None else None,
                "realized_pnl": to_db_str(quantize_money(h.realized_pnl)),
                "oversold_shares": to_db_str(h.oversold_shares) if h.oversold_shares > ZERO else None,
            }
        )
    return ok(data, meta=Meta(total=len(data)))


@router.get("/summary", summary="组合汇总")
def get_summary(
    currency: str = Query("JPY", description="基准币种 JPY/USD/CNY"),
    session: Session = Depends(get_session),
) -> dict:
    """组合汇总：按基准币种换算后汇总总成本、总市值、总浮盈、总已实现盈亏。

    跨币种通过 fx_rates 换算（缺失回退最近交易日并标记估算）。
    若某币种汇率完全缺失，则在 warnings 中标注，相关金额按原币种并入（可能不准）。
    """
    currency = currency.upper()
    items = pnl_service.compute_all_holdings(session)
    total_cost = ZERO
    total_mv = ZERO
    total_upnl = ZERO
    total_realized = ZERO
    mv_available = True
    estimated = False
    warnings: list[str] = []
    unconverted: set[str] = set()  # 缺汇率、未能并入基准合计的币种

    today = date.today()

    # 若存在与目标币种不同的持仓币种、且当前无任何可用汇率，则联网拉取实时汇率兜底。
    # （已有历史/当天汇率时不覆盖，保证可复现与离线可用。）
    foreign = {ph.stock.currency.upper() for ph in items if ph.stock.currency.upper() != currency}
    if foreign:
        from app.services.data_sync.fx_client import store_live_rates

        missing = []
        for fc in foreign:
            try:
                get_fx_quote(session, fc, currency, today)
            except FxRateUnavailable:
                missing.append(fc)
        if missing:
            try:
                store_live_rates(session, today)
            except Exception:  # noqa: BLE001, S110
                pass

    def _conv(amount: Decimal | None, from_ccy: str) -> Decimal | None:
        """换算到基准币种。

        缺汇率时返回 None（不再把外币原值直接并入基准合计，避免跨币种直接相加），
        并记录该币种到 unconverted，由调用方计入 warnings。
        """
        nonlocal estimated
        if amount is None:
            return None
        if from_ccy == currency:
            return amount
        try:
            q = get_fx_quote(session, from_ccy, currency, today)
            if q.is_estimated:
                estimated = True
            return amount * q.rate
        except FxRateUnavailable:
            unconverted.add(from_ccy)
            return None

    for ph in items:
        h = ph.holding
        ccy = ph.stock.currency
        c = _conv(h.cost_basis, ccy)
        if c is not None:
            total_cost += c
        r = _conv(h.realized_pnl, ccy)
        if r is not None:
            total_realized += r
        mv = h.market_value(ph.last_price)
        if mv is None:
            mv_available = False
        else:
            cmv = _conv(mv, ccy)
            if cmv is None:
                # 该币种市值无法换算 → 基准币种市值合计不完整
                mv_available = False
            else:
                total_mv += cmv
                upnl = h.unrealized_pnl(ph.last_price)
                cupnl = _conv(upnl, ccy)
                if cupnl is not None:
                    total_upnl += cupnl

    for fc in sorted(unconverted):
        warnings.append(f"缺少 {fc}->{currency} 汇率，{fc} 持仓未并入基准币种合计")
    if unconverted:
        estimated = True

    # 数据完整性告警：超卖（卖出超过持仓）与无效公司行动（ratio 缺失/为 0）
    for ph in items:
        if ph.holding.oversold_shares > ZERO:
            warnings.append(
                f"{ph.stock.symbol} 存在超卖 {to_db_str(ph.holding.oversold_shares)} 股"
                f"（卖出数量超过持仓），请检查交易记录"
            )
        if ph.holding.invalid_actions:
            warnings.append(
                f"{ph.stock.symbol} 有 {ph.holding.invalid_actions} 条公司行动因 ratio 无效被跳过"
            )

    return ok(
        {
            "currency": currency,
            "positions": len(items),
            "total_cost": to_db_str(quantize_money(total_cost)),
            "total_market_value": to_db_str(quantize_money(total_mv)) if mv_available else None,
            "total_unrealized_pnl": to_db_str(quantize_money(total_upnl)) if mv_available else None,
            "total_realized_pnl": to_db_str(quantize_money(total_realized)),
            "market_value_available": mv_available,
            "is_estimated": estimated,
            "warnings": warnings,
        }
    )
