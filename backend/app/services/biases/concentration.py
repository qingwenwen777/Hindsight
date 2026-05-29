"""暴露与集中度分析（设计文档 F5.4/F5.5/F7.4）。

维度：行业 / 市场 / 币种。
阈值：单股 > 20%、单行业 > 40%（超阈值标记告警）。
金额按基准币种换算后计算占比。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from sqlmodel import Session

from app.core.currency import FxRateUnavailable, get_fx_quote
from app.services.analysis import pnl as pnl_service

ZERO = Decimal("0")

SINGLE_STOCK_THRESHOLD = Decimal("0.20")  # 单股 20%
SINGLE_INDUSTRY_THRESHOLD = Decimal("0.40")  # 单行业 40%


@dataclass
class ExposureSlice:
    """暴露切片。"""

    key: str
    name: str
    value: Decimal
    weight: Decimal  # 占比 0-1
    over_threshold: bool = False


@dataclass
class ConcentrationReport:
    total_value: Decimal
    currency: str
    by_stock: list[ExposureSlice] = field(default_factory=list)
    by_industry: list[ExposureSlice] = field(default_factory=list)
    by_market: list[ExposureSlice] = field(default_factory=list)
    by_currency: list[ExposureSlice] = field(default_factory=list)
    alerts: list[str] = field(default_factory=list)


def _convert(session: Session, amount: Decimal, from_ccy: str, to_ccy: str) -> Decimal:
    if from_ccy == to_ccy:
        return amount
    try:
        q = get_fx_quote(session, from_ccy, to_ccy, date.today())
        return amount * q.rate
    except FxRateUnavailable:
        return amount  # 兜底原币种


def compute_concentration(session: Session, currency: str = "JPY") -> ConcentrationReport:
    """计算暴露与集中度（按基准币种换算后的市值口径）。"""
    currency = currency.upper()
    holdings = pnl_service.compute_all_holdings(session)

    # 每只持仓的基准币种市值
    entries: list[tuple[str, str, str, str, Decimal]] = []  # (symbol,name,market,industry,value)
    total = ZERO
    for ph in holdings:
        mv = ph.holding.market_value(ph.last_price)
        base_val = mv if mv is not None else ph.holding.cost_basis
        val = _convert(session, base_val, ph.stock.currency, currency)
        industry = ph.stock.industry or "未分类"
        entries.append((ph.stock.symbol, ph.stock.name, ph.stock.market, industry, val))
        total += val

    report = ConcentrationReport(total_value=total, currency=currency)
    if total == ZERO:
        return report

    def _weight(v: Decimal) -> Decimal:
        return v / total

    # 按股票
    for symbol, name, _market, _industry, val in sorted(entries, key=lambda x: x[4], reverse=True):
        w = _weight(val)
        over = w > SINGLE_STOCK_THRESHOLD
        report.by_stock.append(ExposureSlice(symbol, name, val, w, over))
        if over:
            report.alerts.append(
                f"单股集中度过高：{name}({symbol}) 占 {(w * 100):.1f}% > 20%"
            )

    # 聚合工具
    def _aggregate(idx: int) -> dict[str, Decimal]:
        agg: dict[str, Decimal] = {}
        for e in entries:
            key = e[idx]
            agg[key] = agg.get(key, ZERO) + e[4]
        return agg

    # 行业
    for key, val in sorted(_aggregate(3).items(), key=lambda x: x[1], reverse=True):
        w = _weight(val)
        over = w > SINGLE_INDUSTRY_THRESHOLD
        report.by_industry.append(ExposureSlice(key, key, val, w, over))
        if over:
            report.alerts.append(f"单行业集中度过高：{key} 占 {(w * 100):.1f}% > 40%")

    # 市场
    for key, val in sorted(_aggregate(2).items(), key=lambda x: x[1], reverse=True):
        report.by_market.append(ExposureSlice(key, key, val, _weight(val)))

    # 币种（用原始持仓币种）
    ccy_agg: dict[str, Decimal] = {}
    for ph in holdings:
        mv = ph.holding.market_value(ph.last_price)
        base_val = mv if mv is not None else ph.holding.cost_basis
        val = _convert(session, base_val, ph.stock.currency, currency)
        ccy_agg[ph.stock.currency] = ccy_agg.get(ph.stock.currency, ZERO) + val
    for key, val in sorted(ccy_agg.items(), key=lambda x: x[1], reverse=True):
        report.by_currency.append(ExposureSlice(key, key, val, _weight(val)))

    return report
