"""规则筛选引擎 —— 纯确定性计算，不调用任何 AI / 网络。

约定：
- 字段值来自平台已登记 + 已同步的数据（Stock / 最新 Financial / 关注 / 持仓）。
- 百分比类字段（roe / revenue_yoy / profit_yoy / dividend_yield）库内存小数（0.15=15%），
  规则输入按"百分数"语义（>15 表示 15%），引擎内部把库值 ×100 再比较。
- 某标的缺少规则所需字段 → 该条件判为不满足，并记入 missing（不报错）。
- 多条件 AND 组合。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation

from sqlmodel import Session, select

from app.core.money import D
from app.models.financials import Financial
from app.models.stock import Stock
from app.models.transaction import Transaction
from app.models.watchlist import Watchlist

# 数值字段（库内 Decimal）。pct=True 表示库内存小数、规则按百分数。
_NUMERIC_FIELDS: dict[str, bool] = {
    "pe": False,
    "pb": False,
    "eps": False,
    "market_cap": False,
    "roe": True,
    "revenue_yoy": True,
    "profit_yoy": True,
    "dividend_yield": True,
}
_STRING_FIELDS = {"market", "industry", "sector"}
_BOOL_FIELDS = {"in_watchlist", "in_holdings", "is_etf"}

OPERATORS = {"<", "<=", ">", ">=", "=", "between"}

ALL_FIELDS = sorted(set(_NUMERIC_FIELDS) | _STRING_FIELDS | _BOOL_FIELDS)


@dataclass
class ScreenHit:
    """一条命中结果。"""

    stock_id: int
    symbol: str
    name: str
    market: str
    matched: dict[str, str] = field(default_factory=dict)  # field -> 展示值
    missing: list[str] = field(default_factory=list)


def _latest_financial(session: Session, stock_id: int) -> Financial | None:
    return session.exec(
        select(Financial)
        .where(Financial.stock_id == stock_id)
        .order_by(Financial.as_of.desc())
        .limit(1)
    ).first()


def _held_stock_ids(session: Session) -> set[int]:
    """有买入交易且当前可能持仓的股票集合（粗口径：出现过 BUY 即视为关注持有过）。

    为避免对每只跑完整 FIFO，这里用"有交易记录"近似 in_holdings 候选，
    再在判定时用精确持仓校验（compute_holding）。
    """
    return set(session.exec(select(Transaction.stock_id)).all())


def _coerce_number(value) -> Decimal | None:  # noqa: ANN001
    try:
        return D(value)
    except (InvalidOperation, TypeError, ValueError):
        return None


def _cmp(actual: Decimal, op: str, target: Decimal, target2: Decimal | None = None) -> bool:
    if op == "<":
        return actual < target
    if op == "<=":
        return actual <= target
    if op == ">":
        return actual > target
    if op == ">=":
        return actual >= target
    if op == "=":
        return actual == target
    if op == "between" and target2 is not None:
        lo, hi = (target, target2) if target <= target2 else (target2, target)
        return lo <= actual <= hi
    return False


def _resolve_numeric(field_name: str, fin: Financial | None, stock: Stock) -> Decimal | None:
    """取数值字段的可比较值（百分比字段已 ×100）。返回 None 表示数据缺失。"""
    raw = None
    if field_name == "eps" and fin is not None:
        raw = fin.eps
    elif field_name == "market_cap" and fin is not None:
        raw = fin.market_cap
    elif fin is not None:
        raw = getattr(fin, field_name, None)
    if raw is None:
        return None
    val = _coerce_number(raw)
    if val is None:
        return None
    if _NUMERIC_FIELDS.get(field_name):  # 百分比字段：库内小数 → 百分数
        val = val * Decimal("100")
    return val


def _evaluate_condition(
    cond: dict,
    stock: Stock,
    fin: Financial | None,
    in_watchlist: bool,
    in_holdings: bool,
) -> tuple[bool, str | None, str | None]:
    """判定单个条件。

    返回 (是否满足, 命中展示值, 缺失字段名)。
    """
    fname = str(cond.get("field", "")).strip().lower()
    op = str(cond.get("op", "")).strip()

    # 布尔字段
    if fname in _BOOL_FIELDS:
        want = bool(cond.get("value", True))
        if fname == "in_watchlist":
            actual = in_watchlist
        elif fname == "in_holdings":
            actual = in_holdings
        else:  # is_etf
            actual = bool(stock.is_etf)
        ok = actual == want
        return ok, ("是" if actual else "否"), None

    # 字符串字段（等值，忽略大小写）
    if fname in _STRING_FIELDS:
        actual = getattr(stock, fname, None)
        if actual is None:
            return False, None, fname
        target = str(cond.get("value", "")).strip()
        ok = str(actual).strip().lower() == target.lower()
        return ok, str(actual), None

    # 数值字段
    if fname in _NUMERIC_FIELDS:
        actual = _resolve_numeric(fname, fin, stock)
        if actual is None:
            return False, None, fname
        target = _coerce_number(cond.get("value"))
        if target is None:
            return False, None, None
        target2 = _coerce_number(cond.get("value2")) if cond.get("value2") is not None else None
        ok = _cmp(actual, op, target, target2)
        # 展示：百分比字段加 %
        disp = f"{actual:.2f}%" if _NUMERIC_FIELDS[fname] else f"{actual:.2f}"
        return ok, disp, None

    # 未知字段 → 视为缺失
    return False, None, fname or "unknown"


def run_screen(
    session: Session,
    conditions: list[dict],
    markets: list[str] | None = None,
) -> list[ScreenHit]:
    """执行筛选，返回命中列表。纯计算，无 AI。"""
    if not conditions:
        return []

    stmt = select(Stock)
    if markets:
        upper = [m.upper() for m in markets]
        stmt = stmt.where(Stock.market.in_(upper))  # type: ignore[attr-defined]
    stocks = list(session.exec(stmt).all())

    watch_ids = set(session.exec(select(Watchlist.stock_id)).all())
    traded_ids = _held_stock_ids(session)

    # in_holdings 精确判定缓存（仅对需要时计算）
    needs_holdings = any(str(c.get("field", "")).lower() == "in_holdings" for c in conditions)
    held_now: set[int] = set()
    if needs_holdings:
        from app.services.analysis.pnl import compute_holding

        for sid in traded_ids:
            h = compute_holding(session, sid)
            if h.shares > 0:
                held_now.add(sid)

    hits: list[ScreenHit] = []
    for stock in stocks:
        fin = _latest_financial(session, stock.id)  # type: ignore[arg-type]
        in_watch = stock.id in watch_ids
        in_hold = stock.id in held_now

        all_ok = True
        matched: dict[str, str] = {}
        missing: list[str] = []
        for cond in conditions:
            ok, disp, miss = _evaluate_condition(cond, stock, fin, in_watch, in_hold)
            fname = str(cond.get("field", "")).lower()
            if miss:
                missing.append(miss)
            if disp is not None:
                matched[fname] = disp
            if not ok:
                all_ok = False
        if all_ok:
            hits.append(
                ScreenHit(
                    stock_id=stock.id,  # type: ignore[arg-type]
                    symbol=stock.symbol,
                    name=stock.name,
                    market=stock.market,
                    matched=matched,
                    missing=sorted(set(missing)),
                )
            )

    # 按市场+代码稳定排序，保证确定性
    hits.sort(key=lambda h: (h.market, h.symbol))
    return hits


__all__ = ["run_screen", "ScreenHit", "ALL_FIELDS", "OPERATORS"]
