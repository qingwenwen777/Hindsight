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
    benchmark_name: str | None = None
    benchmark_change_pct: Decimal | None = None
    movers: list[MoverRow] = field(default_factory=list)
    touches: list[PriceTouchRow] = field(default_factory=list)
    todos: list[TodoRow] = field(default_factory=list)
    has_any: bool = False  # 是否有任何重点事项


def _last_two_closes(session: Session, stock_id: int) -> tuple[Decimal | None, Decimal | None]:
    rows = session.exec(
        select(Price.close)
        .where(Price.stock_id == stock_id)
        .order_by(Price.date.desc())
        .limit(2)
    ).all()
    if len(rows) >= 2:
        return D(rows[0]), D(rows[1])
    if len(rows) == 1:
        return D(rows[0]), None
    return None, None


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

    # 异动 + 触价
    for sid in stock_ids:
        stock = session.get(Stock, sid)
        if stock is None:
            continue
        last, prev = _last_two_closes(session, sid)
        if last is None:
            continue
        chg = _change_pct(last, prev)
        if chg is not None and abs(chg) >= move_threshold_pct:
            ctx.movers.append(
                MoverRow(
                    symbol=stock.symbol,
                    name=stock.name,
                    stock_id=sid,
                    change_pct=chg,
                    last_price=last,
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
    holdings = compute_all_holdings(session)
    total = sum((ph.holding.market_value(ph.last_price) or ph.holding.cost_basis) for ph in holdings)
    if total and total > ZERO:
        for ph in holdings:
            if ph.stock.market != market:
                continue
            val = ph.holding.market_value(ph.last_price) or ph.holding.cost_basis
            w = val / total * Decimal("100")
            if w > CONCENTRATION_THRESHOLD:
                ctx.todos.append(
                    TodoRow(
                        kind="CONCENTRATION",
                        text=f"{ph.stock.symbol} 占组合 {w:.1f}%，超 20% 集中度阈值",
                        link=f"/stocks/{ph.stock.id}",
                    )
                )

    ctx.has_any = bool(ctx.movers or ctx.touches or ctx.todos)
    return ctx


def _fmt_pct(v: Decimal | None) -> str:
    if v is None:
        return "—"
    return f"{v:+.2f}%"


def render_context_md(ctx: ReportContext) -> str:
    """把上下文渲染成机械版 Markdown（数据部分），供 AI 叙述或降级直接用。"""
    lines: list[str] = []

    lines.append("## 市场概览")
    if ctx.benchmark_name:
        if ctx.benchmark_change_pct is not None:
            lines.append(f"- {ctx.benchmark_name}：{_fmt_pct(ctx.benchmark_change_pct)}")
        else:
            lines.append(f"- {ctx.benchmark_name}：（指数行情未同步）")
    else:
        lines.append("- （无基准数据）")

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


__all__ = ["build_report_context", "render_context_md", "ReportContext"]
