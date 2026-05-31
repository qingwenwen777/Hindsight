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


def invalidate_holdings_cache(stock_id: int | None = None) -> None:  # noqa: ARG001
    """空操作（保留以兼容调用方）。

    历史实现使用进程内字典缓存持仓。该缓存存在两类正确性问题：
    1. 多 worker / 多进程下各进程缓存独立，一个进程写入后其它进程仍读旧值（脏读）；
    2. 命中缓存直接返回共享可变 Holding（含可变 lots），调用方一旦改动会污染缓存。
    且失效时机（commit 前调用）也无法保证一致。为彻底规避这些问题，
    现已移除进程内缓存，compute_holding 每次都基于最新事务重新计算。
    """
    return None


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
    # 超卖（卖出股数超过持仓）累计：用于数据告警，不应静默
    oversold_shares: Decimal = ZERO
    # 被跳过的无效公司行动（ratio 为空/0）计数：用于数据告警
    invalid_actions: int = 0

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


def _consume_fifo(lots: list[list[Decimal]], qty: Decimal) -> tuple[Decimal, Decimal]:
    """从 FIFO 队首消耗 qty 股。

    返回 (实际消耗股数, 被消耗部分的总成本)。
    当 lots 不足以覆盖 qty（超卖）时，实际消耗股数 < qty，调用方据此识别超卖。
    """
    consumed_cost = ZERO
    consumed_qty = ZERO
    remaining = qty
    while remaining > ZERO and lots:
        lot = lots[0]
        lot_qty, lot_cost_per = lot[0], lot[1]
        if lot_qty <= remaining:
            consumed_cost += lot_qty * lot_cost_per
            consumed_qty += lot_qty
            remaining -= lot_qty
            lots.pop(0)
        else:
            consumed_cost += remaining * lot_cost_per
            consumed_qty += remaining
            lot[0] = lot_qty - remaining
            remaining = ZERO
    return consumed_qty, consumed_cost


def _events_from_rows(
    txs: list[Transaction], cas: list[CorporateAction]
) -> list[_Event]:
    """从已加载的交易/公司行动行构建归一化事件并排序（供批量计算复用）。"""
    events: list[_Event] = []
    seq = 0
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
    for ca in cas:
        kind = ca.action_type.upper()
        if kind not in ("SPLIT", "BONUS"):
            continue
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

    def _priority(e: _Event) -> int:
        return 0 if e.kind in ("BUY", "SELL") else 1

    events.sort(key=lambda e: (e.when, _priority(e), e.seq))
    return events


def _compute_from_events(stock_id: int, events: list[_Event]) -> Holding:
    """基于已排序事件计算持仓（_load_events 与批量路径共用的纯计算核心）。"""
    holding = Holding(stock_id=stock_id)
    lots = holding.lots
    for e in events:
        if e.kind == "BUY":
            gross = e.quantity * e.price
            cost_per_share = (gross + e.fees) / e.quantity if e.quantity else ZERO
            lots.append([e.quantity, cost_per_share])
            holding.shares += e.quantity
            holding.cost_basis += e.quantity * cost_per_share
            holding.total_buy_fees += e.fees
        elif e.kind == "SELL":
            sell_qty = e.quantity
            consumed_qty, consumed_cost = _consume_fifo(lots, sell_qty)
            if consumed_qty < sell_qty:
                holding.oversold_shares += sell_qty - consumed_qty
                sell_qty = consumed_qty
            if sell_qty > ZERO:
                proceeds = sell_qty * e.price - e.fees
                holding.shares -= sell_qty
                holding.cost_basis -= consumed_cost
                holding.realized_pnl += proceeds - consumed_cost
            holding.total_sell_fees += e.fees
        elif e.kind in ("SPLIT", "BONUS"):
            if e.ratio_num and e.ratio_den and e.ratio_num > ZERO and e.ratio_den > ZERO:
                ratio = e.ratio_num / e.ratio_den
                holding.shares *= ratio
                for lot in lots:
                    lot[0] *= ratio
                    lot[1] /= ratio
            else:
                holding.invalid_actions += 1
    return holding


def compute_holding(session: Session, stock_id: int, *, use_cache: bool = True) -> Holding:  # noqa: ARG001
    """计算单只股票的持仓与 FIFO 已实现盈亏。

    use_cache 参数已废弃（无进程内缓存），保留签名以兼容调用方。
    每次都基于当前事务最新数据重新计算，多 worker 下不会脏读。
    """
    events = _load_events(session, stock_id)
    return _compute_from_events(stock_id, events)


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
    """计算所有有交易记录的股票的持仓（仅保留 shares>0 的）。

    批量加载：一次性取出全部交易、公司行动、股票、最新收盘价，在内存按
    stock_id 分组计算，避免逐股查询（消除 N+1，约 4N+1 → 4 次查询）。
    """
    from app.models.stock import Price

    txs_all = list(session.exec(select(Transaction)).all())
    if not txs_all:
        return []

    stock_ids = {t.stock_id for t in txs_all}

    # 按 stock_id 分组交易
    txs_by_stock: dict[int, list[Transaction]] = {}
    for t in txs_all:
        txs_by_stock.setdefault(t.stock_id, []).append(t)

    # 一次性取相关公司行动并分组
    cas_by_stock: dict[int, list[CorporateAction]] = {}
    cas_all = session.exec(
        select(CorporateAction).where(CorporateAction.stock_id.in_(stock_ids))  # type: ignore[attr-defined]
    ).all()
    for ca in cas_all:
        cas_by_stock.setdefault(ca.stock_id, []).append(ca)

    # 一次性取相关股票
    stocks_by_id: dict[int, Stock] = {
        s.id: s  # type: ignore[misc]
        for s in session.exec(select(Stock).where(Stock.id.in_(stock_ids))).all()  # type: ignore[attr-defined]
    }

    # 一次性取每只股票的最新收盘价：按 (stock_id, date) 倒序，取每组首行
    from sqlalchemy import func as _func

    latest_dates = dict(
        session.exec(
            select(Price.stock_id, _func.max(Price.date))
            .where(Price.stock_id.in_(stock_ids))  # type: ignore[attr-defined]
            .group_by(Price.stock_id)
        ).all()
    )
    last_price_by_stock: dict[int, Decimal] = {}
    if latest_dates:
        # 用 (stock_id, date) 元组集合一次性取出对应收盘价
        rows = session.exec(
            select(Price.stock_id, Price.date, Price.close).where(
                Price.stock_id.in_(latest_dates.keys())  # type: ignore[attr-defined]
            )
        ).all()
        for sid, d, close in rows:
            if latest_dates.get(sid) == d and close is not None:
                last_price_by_stock[sid] = D(close)

    result: list[PortfolioHolding] = []
    for sid in stock_ids:
        events = _events_from_rows(txs_by_stock.get(sid, []), cas_by_stock.get(sid, []))
        holding = _compute_from_events(sid, events)
        if holding.shares <= ZERO:
            continue
        stock = stocks_by_id.get(sid)
        if stock is None:
            continue
        result.append(
            PortfolioHolding(
                stock=stock,
                holding=holding,
                last_price=last_price_by_stock.get(sid),
            )
        )
    return result
