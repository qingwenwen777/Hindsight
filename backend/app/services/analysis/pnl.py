"""持仓与 FIFO 盈亏计算（设计文档 4.3 / 5.4）。

口径钦定：
- FIFO 为账面 / 报税口径（已实现盈亏）。
- 加权平均仅作 UI 参考均价展示。
- 公司行动（SPLIT/BONUS）为乘法型：持股数 × ratio，单股成本 ÷ ratio。
- 费用计入成本：买入成本 = quantity*price + 买入费用；卖出收入 = quantity*price - 卖出费用。
- 全程 Decimal，无浮点。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from sqlmodel import Session, select

from app.core.money import D
from app.models.corporate_action import CorporateAction
from app.models.stock import Stock
from app.models.transaction import Transaction

ZERO = Decimal("0")

# 进程内持仓缓存（stock_id -> Holding）。交易写入时失效。
_holdings_cache: dict[int, "Holding"] = {}


def invalidate_holdings_cache(stock_id: int | None = None) -> None:
    """失效持仓缓存。stock_id 为空则清空全部。"""
    if stock_id is None:
        _holdings_cache.clear()
    else:
        _holdings_cache.pop(stock_id, None)


@dataclass
class _Event:
    """归一化事件（交易 + 公司行动），按日期 + 类型优先级排序。"""

    when: date
    kind: str  # BUY / SELL / SPLIT / BONUS
    quantity: Decimal = ZERO
    price: Decimal = ZERO
    fees: Decimal = ZERO
    ratio_num: Decimal = ZERO
    ratio_den: Decimal = ZERO
    seq: int = 0  # 同日稳定排序


@dataclass
class Holding:
    """某只股票的持仓快照。"""

    stock_id: int
    shares: Decimal = ZERO  # 当前持股
    cost_basis: Decimal = ZERO  # 当前持仓总成本（FIFO 剩余 lot 成本和）
    realized_pnl: Decimal = ZERO  # 已实现盈亏（FIFO）
    total_buy_fees: Decimal = ZERO
    total_sell_fees: Decimal = ZERO
    # FIFO 剩余批次 [[剩余股数, 单股成本], ...]
    lots: list[list[Decimal]] = field(default_factory=list)

    @property
    def avg_cost(self) -> Decimal:
        """当前持仓的 FIFO 单股成本（参考）。"""
        if self.shares == ZERO:
            return ZERO
        return self.cost_basis / self.shares

    def market_value(self, last_price: Decimal | None) -> Decimal | None:
        """按最新价算市值。"""
        if last_price is None:
            return None
        return self.shares * last_price

    def unrealized_pnl(self, last_price: Decimal | None) -> Decimal | None:
        """浮动盈亏 = 市值 - 成本。"""
        mv = self.market_value(last_price)
        if mv is None:
            return None
        return mv - self.cost_basis


def _load_events(session: Session, stock_id: int) -> list[_Event]:
    """加载交易 + 公司行动，归一化并按时间排序。

    同一天的排序优先级：BUY/SELL 先于公司行动？
    实务上除权日的拆股在当日交易前生效，但用户录入的 BUY/SELL 通常是除权后口径。
    这里约定：公司行动在"当日交易之后"应用前的持仓上不影响已录交易价；
    为简化且符合直觉，按 (日期, 类型优先级) 排序：同日先处理交易，再处理公司行动。
    """
    events: list[_Event] = []
    seq = 0

    txs = session.exec(
        select(Transaction).where(Transaction.stock_id == stock_id)
    ).all()
    for t in txs:
        fees = (t.commission or ZERO) + (t.tax or ZERO) + (t.other_fees or ZERO)
        events.append(
            _Event(
                when=t.trade_date,
                kind=t.type.upper(),
                quantity=D(t.quantity),
                price=D(t.price),
                fees=D(fees),
                seq=seq,
            )
        )
        seq += 1

    cas = session.exec(
        select(CorporateAction).where(CorporateAction.stock_id == stock_id)
    ).all()
    for ca in cas:
        kind = ca.action_type.upper()
        if kind not in ("SPLIT", "BONUS"):
            continue  # RIGHTS/MERGE 暂不在 FIFO 乘法型处理（Phase 2 扩展）
        events.append(
            _Event(
                when=ca.ex_date,
                kind=kind,
                ratio_num=D(ca.ratio_num) if ca.ratio_num else ZERO,
                ratio_den=D(ca.ratio_den) if ca.ratio_den else ZERO,
                seq=seq,
            )
        )
        seq += 1

    # 类型优先级：同日交易(0) 先于公司行动(1)
    def _priority(e: _Event) -> int:
        return 0 if e.kind in ("BUY", "SELL") else 1

    events.sort(key=lambda e: (e.when, _priority(e), e.seq))
    return events


def _consume_fifo(lots: list[list[Decimal]], qty: Decimal) -> Decimal:
    """从 FIFO 队首消耗 qty 股，返回被消耗部分的总成本。"""
    consumed_cost = ZERO
    remaining = qty
    while remaining > ZERO and lots:
        lot = lots[0]
        lot_qty, lot_cost_per = lot[0], lot[1]
        if lot_qty <= remaining:
            consumed_cost += lot_qty * lot_cost_per
            remaining -= lot_qty
            lots.pop(0)
        else:
            consumed_cost += remaining * lot_cost_per
            lot[0] = lot_qty - remaining
            remaining = ZERO
    return consumed_cost


def compute_holding(session: Session, stock_id: int, *, use_cache: bool = True) -> Holding:
    """计算单只股票的持仓与 FIFO 已实现盈亏。"""
    if use_cache and stock_id in _holdings_cache:
        return _holdings_cache[stock_id]

    events = _load_events(session, stock_id)
    holding = Holding(stock_id=stock_id)
    lots = holding.lots

    for e in events:
        if e.kind == "BUY":
            # 单股成本 = (数量*价 + 买入费) / 数量
            gross = e.quantity * e.price
            cost_per_share = (gross + e.fees) / e.quantity if e.quantity else ZERO
            lots.append([e.quantity, cost_per_share])
            holding.shares += e.quantity
            holding.cost_basis += e.quantity * cost_per_share
            holding.total_buy_fees += e.fees
        elif e.kind == "SELL":
            sell_qty = e.quantity
            # 卖出收入（净额，扣卖出费用）
            proceeds = e.quantity * e.price - e.fees
            consumed_cost = _consume_fifo(lots, sell_qty)
            holding.shares -= sell_qty
            holding.cost_basis -= consumed_cost
            holding.realized_pnl += proceeds - consumed_cost
            holding.total_sell_fees += e.fees
        elif e.kind in ("SPLIT", "BONUS"):
            if e.ratio_den and e.ratio_den != ZERO and e.ratio_num:
                ratio = e.ratio_num / e.ratio_den
                holding.shares *= ratio
                for lot in lots:
                    lot[0] *= ratio  # 股数乘
                    lot[1] /= ratio  # 单股成本除（稀释）
                # cost_basis 不变（乘除抵消），保持总成本
    if use_cache:
        _holdings_cache[stock_id] = holding
    return holding


@dataclass
class PortfolioHolding:
    """组合层面单只持仓（含市值/浮盈，需最新价）。"""

    stock: Stock
    holding: Holding
    last_price: Decimal | None


def _latest_price(session: Session, stock_id: int) -> Decimal | None:
    """取最新收盘价（用于市值/浮盈）。"""
    from app.models.stock import Price

    stmt = (
        select(Price.close)
        .where(Price.stock_id == stock_id)
        .order_by(Price.date.desc())
        .limit(1)
    )
    row = session.exec(stmt).first()
    return D(row) if row is not None else None


def compute_all_holdings(session: Session) -> list[PortfolioHolding]:
    """计算所有有交易记录的股票的持仓（仅保留 shares>0 的）。"""
    stock_ids = set(session.exec(select(Transaction.stock_id)).all())
    result: list[PortfolioHolding] = []
    for sid in stock_ids:
        holding = compute_holding(session, sid)
        if holding.shares <= ZERO:
            continue
        stock = session.get(Stock, sid)
        if stock is None:
            continue
        result.append(
            PortfolioHolding(
                stock=stock,
                holding=holding,
                last_price=_latest_price(session, sid),
            )
        )
    return result
