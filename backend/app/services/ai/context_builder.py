"""上下文组装（设计文档 5.5）—— 数字由代码算，AI 只做定性。"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from sqlmodel import Session, select

from app.core.money import D
from app.models.journal import Journal
from app.models.stock import Price, Stock
from app.models.transaction import Transaction


def _price_on_or_after(session: Session, stock_id: int, on: date) -> Decimal | None:
    row = session.exec(
        select(Price.close)
        .where(Price.stock_id == stock_id, Price.date >= on)
        .order_by(Price.date)
        .limit(1)
    ).first()
    return D(row) if row is not None else None


def calc_return_pct(
    session: Session, stock_id: int, from_date: date, days: int
) -> Decimal | None:
    """从 from_date 到 +days 的价格回报百分比（代码精确计算）。"""
    p0 = _price_on_or_after(session, stock_id, from_date)
    p1 = _price_on_or_after(session, stock_id, from_date + timedelta(days=days))
    if p0 is None or p1 is None or p0 == 0:
        return None
    return (p1 - p0) / p0 * Decimal("100")


def _fmt(v: Decimal | None, suffix: str = "%") -> str:
    if v is None:
        return "数据不足"
    return f"{v:+.2f}{suffix}"


def build_trade_review_context(session: Session, transaction_id: int) -> str:
    """组装交易复盘上下文。"""
    tx = session.get(Transaction, transaction_id)
    if not tx:
        raise ValueError("交易不存在")
    stock = session.get(Stock, tx.stock_id)
    journal = session.get(Journal, tx.journal_id) if tx.journal_id else None

    return_30d = calc_return_pct(session, tx.stock_id, tx.trade_date, 30)

    j_lines = "（无关联日志）"
    if journal:
        j_lines = (
            f"- 类型: {journal.thesis_category or '—'}\n"
            f"- 预期持有: {journal.expected_horizon or '—'}\n"
            f"- 目标价: {journal.target_price or '—'} | 止损: {journal.stop_loss_price or '—'}\n"
            f"- 信心(1-5): {journal.confidence or '—'}\n"
            f"- 情绪: {journal.emotion or '—'}\n"
            f"- 主要逻辑: {journal.thesis}\n"
            f"- 主要风险: {journal.risks or '—'}"
        )

    # 决策时财务数据（代码取，AI 不得编造）
    fin_lines = "（无财务数据）"
    fin = _latest_financial(session, tx.stock_id)
    if fin:
        def _pct(v):  # noqa: ANN202
            return f"{float(v) * 100:.1f}%" if v is not None else "—"

        fin_lines = (
            f"- PE: {fin.pe or '—'} | PB: {fin.pb or '—'} | ROE(TTM): {_pct(fin.roe)}\n"
            f"- 营收 YoY: {_pct(fin.revenue_yoy)} | 净利 YoY: {_pct(fin.profit_yoy)}\n"
            f"- 数据日期: {fin.as_of.isoformat()}"
        )

    return f"""## 交易信息
- 股票: {stock.name} ({stock.symbol})
- 方向: {tx.type} | 日期: {tx.trade_date}
- 价格: {tx.price} {tx.currency} | 数量: {tx.quantity}

## 决策日志(用户当时写的)
{j_lines}

## 决策后实际走势(代码计算,精确)
- 30 天回报: {_fmt(return_30d)}

## 财务/估值数据(代码取,精确)
{fin_lines}

> 注：以上数字由系统精确计算/获取，请仅基于这些数据做定性分析。
"""


def _latest_financial(session: Session, stock_id: int):  # noqa: ANN202
    """取最新财务快照。"""
    from app.models.financials import Financial

    return session.exec(
        select(Financial)
        .where(Financial.stock_id == stock_id)
        .order_by(Financial.as_of.desc())
        .limit(1)
    ).first()


def build_devils_advocate_context(session: Session, journal_id: int) -> str:
    """组装魔鬼代言人上下文（基于一篇决策日志）。"""
    journal = session.get(Journal, journal_id)
    if not journal:
        raise ValueError("日志不存在")
    stock = session.get(Stock, journal.stock_id)
    return (
        f"股票: {stock.name}({stock.symbol})\n"
        f"决策类型: {journal.decision_type} | 论点: {journal.thesis_category or '—'}\n"
        f"目标价: {journal.target_price or '—'} | 止损: {journal.stop_loss_price or '—'}\n"
        f"信心: {journal.confidence or '—'} | 情绪: {journal.emotion or '—'}\n"
        f"投资逻辑: {journal.thesis}\n"
        f"自述风险: {journal.risks or '—'}"
    )


def build_failure_pattern_context(
    session: Session, start: date, end: date, loss_threshold_pct: Decimal = Decimal("5")
) -> str:
    """组装失败模式上下文：区间内亏损 > 阈值 的交易摘要。

    简化口径：对每笔 SELL，用 30 天前后价无关，这里用交易记录 + 关联日志摘要，
    亏损判定基于 journal 复盘或后续价格回报（此处用 30 天回报近似）。
    """
    txs = session.exec(
        select(Transaction).where(
            Transaction.trade_date >= start, Transaction.trade_date <= end
        )
    ).all()
    lines: list[str] = []
    for tx in txs:
        ret = calc_return_pct(session, tx.stock_id, tx.trade_date, 30)
        if ret is None:
            continue
        # BUY 后下跌 或 SELL 后上涨 视为"判断偏差"，这里聚焦买入后亏损
        is_loss = tx.type == "BUY" and ret < -loss_threshold_pct
        if not is_loss:
            continue
        stock = session.get(Stock, tx.stock_id)
        journal = session.get(Journal, tx.journal_id) if tx.journal_id else None
        emotion = journal.emotion if journal else "—"
        horizon = journal.expected_horizon if journal else "—"
        lines.append(
            f"- tx#{tx.id} {stock.symbol} {tx.type} @{tx.trade_date} "
            f"30天回报 {ret:+.1f}% 情绪={emotion} 预期持有={horizon}"
        )
    if not lines:
        return "（该区间无亏损 > {0}% 的买入交易）".format(loss_threshold_pct)
    return "\n".join(lines)


def build_chat_context(session: Session, refs: list[tuple[str, int]]) -> str:
    """组装对话引用上下文（持仓/交易/日志）。

    refs: [(type, id)]，type ∈ {HOLDING, TRANSACTION, JOURNAL}。
    持仓数字由 pnl 服务精确计算。
    """
    from app.services.analysis import pnl as pnl_service

    parts: list[str] = []
    for rtype, rid in refs:
        rtype = rtype.upper()
        if rtype in ("HOLDING", "STOCK"):
            stock = session.get(Stock, rid)
            if not stock:
                continue
            holding = pnl_service.compute_holding(session, rid, use_cache=False)
            parts.append(
                f"[持仓] {stock.name}({stock.symbol}) "
                f"持股 {holding.shares} 成本基础 {holding.cost_basis} "
                f"已实现盈亏 {holding.realized_pnl}"
            )
        elif rtype == "TRANSACTION":
            tx = session.get(Transaction, rid)
            if not tx:
                continue
            stock = session.get(Stock, tx.stock_id)
            parts.append(
                f"[交易] tx#{tx.id} {stock.symbol} {tx.type} "
                f"{tx.quantity}@{tx.price}{tx.currency} @{tx.trade_date}"
            )
        elif rtype == "JOURNAL":
            j = session.get(Journal, rid)
            if not j:
                continue
            stock = session.get(Stock, j.stock_id)
            parts.append(
                f"[日志] journal#{j.id} {stock.symbol} {j.decision_type} "
                f"情绪={j.emotion or '—'} 信心={j.confidence or '—'} 逻辑：{j.thesis}"
            )
    if not parts:
        return "（用户未选择具体上下文）"
    return "\n".join(parts)
