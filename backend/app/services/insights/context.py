"""日报上下文组装 —— 所有数字由代码精确计算，AI 只做定性叙述。

输出一个结构化的 `ReportContext`，既能直接渲染成"机械版" Markdown（降级用），
也能塞进 AI 提示让模型叙述。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from sqlmodel import Session, select

from app.core.money import D
from app.models.journal import Journal
from app.models.stock import Price, Stock
from app.models.watchlist import Watchlist
from app.services.analysis.benchmark import DEFAULT_BENCHMARKS
from app.services.analysis.pnl import compute_all_holdings
from app.services.analysis.reminders import compute_reminders

ZERO = Decimal("0")
CONCENTRATION_THRESHOLD = Decimal("20")  # 单标的权重 % 告警阈值


@dataclass
class MoverRow:
    symbol: str
    name: str
    stock_id: int
    change_pct: Decimal
    last_price: Decimal


@dataclass
class HoldingRow:
    """持仓快照（喂给 AI 做"我的组合"复盘的核心信息）。"""

    symbol: str
    name: str
    stock_id: int
    weight_pct: Decimal  # 占组合权重 %
    unrealized_pnl_pct: Decimal | None  # 浮动盈亏 %
    hold_days: int | None  # 首次买入至今天数
    thesis_category: str | None  # 当初决策类别
    thesis: str | None  # 当初投资逻辑摘要
    change_pct: Decimal | None  # 当日涨跌 %


@dataclass
class PriceTouchRow:
    symbol: str
    name: str
    stock_id: int
    journal_id: int
    kind: str  # TARGET | STOP
    threshold: Decimal
    last_price: Decimal


@dataclass
class TodoRow:
    kind: str  # REVIEW | CONCENTRATION
    text: str
    link: str | None = None


@dataclass
class ReportContext:
    market: str
    on_date: date
    data_as_of: date | None = None  # 行情数据实际截止日期
    is_stale: bool = False  # 行情是否过期（最新交易日 < 报告日）
    benchmark_name: str | None = None
    benchmark_change_pct: Decimal | None = None
    holdings: list[HoldingRow] = field(default_factory=list)
    movers: list[MoverRow] = field(default_factory=list)
    touches: list[PriceTouchRow] = field(default_factory=list)
    todos: list[TodoRow] = field(default_factory=list)
    prev_report_excerpt: str | None = None  # 上一篇日报摘录（连续性）
    has_any: bool = False  # 是否有任何重点事项


def _last_two_closes_with_dates(
    session: Session, stock_id: int
) -> tuple[Decimal | None, date | None, Decimal | None]:
    """取最近两条收盘价及最新那条的日期。

    返回 (最新收盘, 最新日期, 前一收盘)。用不同日期的两条记录算"当日涨跌"，
    避免把跨周/停更的价差当成今日异动。
    """
    rows = session.exec(
        select(Price.close, Price.date)
        .where(Price.stock_id == stock_id)
        .order_by(Price.date.desc())
        .limit(2)
    ).all()
    if len(rows) >= 2:
        return D(rows[0][0]), rows[0][1], D(rows[1][0])
    if len(rows) == 1:
        return D(rows[0][0]), rows[0][1], None
    return None, None, None


def _last_two_closes(session: Session, stock_id: int) -> tuple[Decimal | None, Decimal | None]:
    last, _d, prev = _last_two_closes_with_dates(session, stock_id)
    return last, prev


def _change_pct(last: Decimal | None, prev: Decimal | None) -> Decimal | None:
    if last is None or prev is None or prev == ZERO:
        return None
    return (last - prev) / prev * Decimal("100")


def _benchmark_change(session: Session, market: str) -> tuple[str | None, Decimal | None]:
    """市场概览：用基准指数最近两日 close 算涨跌幅（若指数已登记同步）。"""
    bench = DEFAULT_BENCHMARKS.get(market.upper())
    if not bench:
        return None, None
    stock = session.exec(
        select(Stock).where(Stock.symbol == bench["symbol"], Stock.market == market.upper())
    ).first()
    if stock is None:
        # 指数未登记，仅返回名称
        return bench["name"], None
    last, prev = _last_two_closes(session, stock.id)  # type: ignore[arg-type]
    return bench["name"], _change_pct(last, prev)


def _market_stock_ids(session: Session, market: str) -> set[int]:
    """该市场的"持仓 ∪ 关注"标的集合。"""
    market = market.upper()
    ids: set[int] = set()
    # 持仓
    for ph in compute_all_holdings(session):
        if ph.stock.market == market:
            ids.add(ph.stock.id)  # type: ignore[arg-type]
    # 关注
    watch_ids = session.exec(select(Watchlist.stock_id)).all()
    for sid in watch_ids:
        st = session.get(Stock, sid)
        if st and st.market == market:
            ids.add(sid)
    return ids


def _latest_journal_targets(session: Session, stock_id: int) -> Journal | None:
    """取该股最近一条带目标价/止损价的日志。"""
    rows = session.exec(
        select(Journal)
        .where(Journal.stock_id == stock_id)
        .order_by(Journal.created_at.desc())
    ).all()
    for j in rows:
        if j.target_price is not None or j.stop_loss_price is not None:
            return j
    return None


def _latest_journal(session: Session, stock_id: int) -> Journal | None:
    """取该股最近一条决策日志（用于提取当初的投资逻辑/类别）。"""
    return session.exec(
        select(Journal)
        .where(Journal.stock_id == stock_id)
        .order_by(Journal.created_at.desc())
        .limit(1)
    ).first()


def _first_buy_date(session: Session, stock_id: int) -> date | None:
    """该股最早一笔买入日期（用于算持有天数）。"""
    from app.models.transaction import Transaction

    return session.exec(
        select(Transaction.trade_date)
        .where(Transaction.stock_id == stock_id, Transaction.type == "BUY")
        .order_by(Transaction.trade_date.asc())
        .limit(1)
    ).first()


def _prev_report_excerpt(session: Session, market: str, on_date: date) -> str | None:
    """取上一篇该市场日报的正文摘录（连续性：让 AI 跟进昨日关注点）。"""
    from app.models.insight import InsightDocument

    prev = session.exec(
        select(InsightDocument)
        .where(
            InsightDocument.doc_type == "DAILY_REPORT",
            InsightDocument.market == market,
            InsightDocument.report_date < on_date,
        )
        .order_by(InsightDocument.report_date.desc())
        .limit(1)
    ).first()
    if prev is None or not prev.body_md:
        return None
    # 去掉数据明细 details 块，仅取叙述前半部分，限长
    body = prev.body_md.split("<details>")[0].strip()
    excerpt = body[:1200]
    return f"（{prev.report_date}）\n{excerpt}"


def build_report_context(
    session: Session,
    market: str,
    move_threshold_pct: Decimal,
    on_date: date | None = None,
) -> ReportContext:
    """组装某市场日报上下文（数字全部代码算）。"""
    market = market.upper()
    on_date = on_date or date.today()
    ctx = ReportContext(market=market, on_date=on_date)

    # 市场概览
    ctx.benchmark_name, ctx.benchmark_change_pct = _benchmark_change(session, market)

    stock_ids = _market_stock_ids(session, market)

    # 全组合持仓（用于权重、盈亏、当日涨跌的统一计算）
    all_holdings = compute_all_holdings(session)
    total_value = sum(
        (ph.holding.market_value(ph.last_price) or ph.holding.cost_basis) for ph in all_holdings
    )
    holdings_by_sid = {ph.stock.id: ph for ph in all_holdings}

    # 记录行情数据的最新日期（取本市场所有标的里最新的一条），判断是否过期
    latest_data_date: date | None = None

    # 逐标的：当日涨跌 + 异动 + 触价
    change_by_sid: dict[int, Decimal | None] = {}
    for sid in stock_ids:
        stock = session.get(Stock, sid)
        if stock is None:
            continue
        last, last_date, prev = _last_two_closes_with_dates(session, sid)
        if last_date is not None and (latest_data_date is None or last_date > latest_data_date):
            latest_data_date = last_date
        if last is None:
            continue
        chg = _change_pct(last, prev)
        change_by_sid[sid] = chg
        if chg is not None and abs(chg) >= move_threshold_pct:
            ctx.movers.append(
                MoverRow(
                    symbol=stock.symbol, name=stock.name, stock_id=sid,
                    change_pct=chg, last_price=last,
                )
            )
        # 触价
        j = _latest_journal_targets(session, sid)
        if j is not None:
            if j.target_price is not None and last >= D(j.target_price):
                ctx.touches.append(
                    PriceTouchRow(stock.symbol, stock.name, sid, j.id, "TARGET", D(j.target_price), last)  # type: ignore[arg-type]
                )
            if j.stop_loss_price is not None and last <= D(j.stop_loss_price):
                ctx.touches.append(
                    PriceTouchRow(stock.symbol, stock.name, sid, j.id, "STOP", D(j.stop_loss_price), last)  # type: ignore[arg-type]
                )

    ctx.movers.sort(key=lambda m: abs(m.change_pct), reverse=True)

    # 行情新鲜度：最新数据日期 < 报告日 视为过期
    ctx.data_as_of = latest_data_date
    ctx.is_stale = latest_data_date is not None and latest_data_date < on_date

    # 我的持仓快照（本市场）：权重 / 浮盈 / 持有天数 / 当初逻辑 / 当日涨跌
    for sid in stock_ids:
        ph = holdings_by_sid.get(sid)
        if ph is None:
            continue  # 仅关注、未持仓的标的不进持仓快照
        stock = ph.stock
        val = ph.holding.market_value(ph.last_price) or ph.holding.cost_basis
        weight = (val / total_value * Decimal("100")) if total_value and total_value > ZERO else ZERO
        upnl = ph.holding.unrealized_pnl(ph.last_price)
        cost = ph.holding.cost_basis
        upnl_pct = (upnl / cost * Decimal("100")) if (upnl is not None and cost and cost > ZERO) else None
        fb = _first_buy_date(session, sid)
        hold_days = (on_date - fb).days if fb else None
        j = _latest_journal(session, sid)
        thesis = (j.thesis[:120] if j and j.thesis else None)
        ctx.holdings.append(
            HoldingRow(
                symbol=stock.symbol, name=stock.name, stock_id=sid,
                weight_pct=weight, unrealized_pnl_pct=upnl_pct,
                hold_days=hold_days,
                thesis_category=(j.thesis_category if j else None),
                thesis=thesis,
                change_pct=change_by_sid.get(sid),
            )
        )
    ctx.holdings.sort(key=lambda h: h.weight_pct, reverse=True)

    # 待办：复盘到期（该市场相关）+ 集中度
    for r in compute_reminders(session):
        st = session.get(Stock, r.stock_id)
        if st and st.market == market:
            ctx.todos.append(
                TodoRow(
                    kind="REVIEW",
                    text=f"{r.name}({r.symbol}) 决策已 {r.days_since} 天，{r.due_milestone} 天里程碑待复盘",
                    link=f"/journals/{r.journal_id}",
                )
            )

    # 集中度（全组合口径，只在对应市场日报里提相关标的）
    if total_value and total_value > ZERO:
        for ph in all_holdings:
            if ph.stock.market != market:
                continue
            val = ph.holding.market_value(ph.last_price) or ph.holding.cost_basis
            w = val / total_value * Decimal("100")
            if w > CONCENTRATION_THRESHOLD:
                ctx.todos.append(
                    TodoRow(
                        kind="CONCENTRATION",
                        text=f"{ph.stock.symbol} 占组合 {w:.1f}%，超 20% 集中度阈值",
                        link=f"/stocks/{ph.stock.id}",
                    )
                )

    # 连续性：上一篇日报摘录
    ctx.prev_report_excerpt = _prev_report_excerpt(session, market, on_date)

    # 是否有"实质事件"（C：事件驱动判定 —— 持仓快照不算事件）
    ctx.has_any = bool(ctx.movers or ctx.touches or ctx.todos)
    return ctx


def _fmt_pct(v: Decimal | None) -> str:
    if v is None:
        return "—"
    return f"{v:+.2f}%"


def _fmt_signed(v: Decimal | None) -> str:
    if v is None:
        return "—"
    return f"{v:+.1f}%"


def render_context_md(ctx: ReportContext) -> str:
    """把上下文渲染成机械版 Markdown（数据部分），供 AI 叙述或降级直接用。"""
    lines: list[str] = []

    # 数据新鲜度声明（B：标注口径，避免把跨日价差当今日异动）
    if ctx.data_as_of is not None:
        stale = "（数据已过期，非当日）" if ctx.is_stale else ""
        lines.append(f"> 行情数据截止：{ctx.data_as_of.isoformat()}{stale}\n")

    lines.append("## 市场概览")
    if ctx.benchmark_name:
        if ctx.benchmark_change_pct is not None:
            lines.append(f"- {ctx.benchmark_name}：{_fmt_pct(ctx.benchmark_change_pct)}")
        else:
            lines.append(f"- {ctx.benchmark_name}：（指数行情未同步）")
    else:
        lines.append("- （无基准数据）")

    # A：我的持仓快照（成本/盈亏/权重/持有天数/当初逻辑）
    lines.append("\n## 我的持仓快照")
    if ctx.holdings:
        for h in ctx.holdings:
            parts = [f"权重 {h.weight_pct:.1f}%"]
            if h.unrealized_pnl_pct is not None:
                parts.append(f"浮盈 {_fmt_signed(h.unrealized_pnl_pct)}")
            if h.hold_days is not None:
                parts.append(f"持有 {h.hold_days} 天")
            if h.change_pct is not None:
                parts.append(f"当日 {_fmt_signed(h.change_pct)}")
            meta = "，".join(parts)
            line = f"- [{h.symbol}](/stocks/{h.stock_id}) {h.name}：{meta}"
            if h.thesis_category:
                line += f"；当初类别：{h.thesis_category}"
            if h.thesis:
                line += f"；逻辑：{h.thesis}"
            lines.append(line)
    else:
        lines.append("- （本市场无持仓）")

    lines.append("\n## 我的持仓/关注异动")
    if ctx.movers:
        for m in ctx.movers:
            lines.append(
                f"- [{m.symbol}](/stocks/{m.stock_id}) {m.name}：{_fmt_pct(m.change_pct)}（现价 {m.last_price}）"
            )
    else:
        lines.append("- 今日无超阈值异动")

    lines.append("\n## 触及目标价/止损价")
    if ctx.touches:
        for tch in ctx.touches:
            label = "目标价" if tch.kind == "TARGET" else "止损价"
            lines.append(
                f"- [{tch.symbol}](/stocks/{tch.stock_id}) {tch.name} 触及{label} {tch.threshold}"
                f"（现价 {tch.last_price}，对照 [决策日志](/journals/{tch.journal_id})）"
            )
    else:
        lines.append("- 无触及")

    lines.append("\n## 今日待办")
    if ctx.todos:
        for td in ctx.todos:
            link = f"（{td.link}）" if td.link else ""
            lines.append(f"- {td.text}{link}")
    else:
        lines.append("- 无")

    return "\n".join(lines)


def render_context_for_ai(ctx: ReportContext) -> str:
    """喂给 AI 的上下文：机械数据 + 上一篇日报摘录（连续性）。

    上一篇摘录只进 AI 提示、不进存档的"数据明细"，让 AI 跟进昨日关注点。
    """
    md = render_context_md(ctx)
    if ctx.prev_report_excerpt:
        md += f"\n\n## 上一篇日报摘录（用于连续跟进）\n{ctx.prev_report_excerpt}"
    return md


__all__ = ["build_report_context", "render_context_md", "render_context_for_ai", "ReportContext"]
