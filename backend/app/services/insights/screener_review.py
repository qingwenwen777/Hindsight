"""筛选结果的 AI 定性点评 —— 多空/风险/待调研，禁买卖结论。"""

from __future__ import annotations

from datetime import date

from sqlmodel import Session, select

from app.logging_config import get_logger
from app.models.financials import Financial
from app.models.insight import InsightDocument
from app.models.stock import Price, Stock
from app.services.ai import client as ai_client
from app.services.ai import prompts
from app.services.ai.budget import BudgetExceeded
from app.services.screener.engine import ScreenHit

log = get_logger(__name__)

DISCLAIMER = "\n\n---\n*AI 仅供参考，不构成投资建议，不预测股价、不提供买卖信号。*"

_LANG_LABEL = {"zh": "简体中文", "ja": "日本語", "en": "English"}


def _latest_close(session: Session, stock_id: int):  # noqa: ANN202
    return session.exec(
        select(Price.close).where(Price.stock_id == stock_id).order_by(Price.date.desc()).limit(1)
    ).first()


def _latest_financial(session: Session, stock_id: int) -> Financial | None:
    return session.exec(
        select(Financial)
        .where(Financial.stock_id == stock_id)
        .order_by(Financial.as_of.desc())
        .limit(1)
    ).first()


def build_screener_context(session: Session, hits: list[ScreenHit]) -> str:
    """为点评组装精确数据上下文（每标的财务+价格快照）。"""
    parts: list[str] = []
    for h in hits:
        fin = _latest_financial(session, h.stock_id)
        close = _latest_close(session, h.stock_id)

        def _pct(v):  # noqa: ANN202
            return f"{float(v) * 100:.1f}%" if v is not None else "—"

        fin_line = "（无财务数据）"
        if fin:
            fin_line = (
                f"PE={fin.pe or '—'} PB={fin.pb or '—'} ROE(TTM)={_pct(fin.roe)} "
                f"营收YoY={_pct(fin.revenue_yoy)} 净利YoY={_pct(fin.profit_yoy)} "
                f"股息率={_pct(fin.dividend_yield)}"
            )
        parts.append(
            f"### {h.name}（{h.symbol} · {h.market}）\n"
            f"- 最新价：{close if close is not None else '—'}\n"
            f"- 财务：{fin_line}\n"
            f"- 命中规则字段：{', '.join(f'{k}={v}' for k, v in h.matched.items()) or '—'}"
        )
    return "\n\n".join(parts) if parts else "（无标的）"


def review_hits(
    session: Session,
    hits: list[ScreenHit],
    *,
    language: str = "zh",
    rule_name: str | None = None,
) -> InsightDocument:
    """对筛选命中做 AI 点评并存为文档。AI 不可用则降级。"""
    title = f"筛选点评 · {rule_name or '自定义规则'} · {date.today().isoformat()}"
    context = build_screener_context(session, hits)
    symbols = [h.symbol for h in hits]

    if not hits:
        body = f"# {title}\n\n> 筛选无命中标的。{DISCLAIMER}"
        return _save(session, title, body, symbols, degraded=False)

    if not ai_client.is_available():
        body = f"# {title}\n\n> （AI 未配置，仅列出命中标的与数据）\n\n{context}{DISCLAIMER}"
        return _save(session, title, body, symbols, degraded=True, reason="AI 未配置")

    user_prompt = prompts.render_screener_review(
        context, language=_LANG_LABEL.get(language, "简体中文")
    )
    try:
        result = ai_client.analyze(
            session,
            prompt_type="SCREENER_REVIEW",
            system_prompt=prompts.SYSTEM_BASE,
            user_content=user_prompt,
            target_type="PORTFOLIO",
            target_id=None,
            max_tokens=2000,
        )
    except BudgetExceeded as e:
        body = f"# {title}\n\n> （{e}，仅列出命中标的与数据）\n\n{context}{DISCLAIMER}"
        return _save(session, title, body, symbols, degraded=True, reason=str(e))
    except Exception as e:  # noqa: BLE001
        log.warning("screener_review.ai_failed", error=str(e))
        body = f"# {title}\n\n> （AI 调用失败，仅列出命中标的与数据）\n\n{context}{DISCLAIMER}"
        return _save(session, title, body, symbols, degraded=True, reason=f"AI 调用失败：{e}")

    body = (
        f"# {title}\n\n{result.response}\n\n---\n\n"
        f"<details>\n<summary>命中数据明细</summary>\n\n{context}\n\n</details>"
    )
    return _save(
        session, title, body, symbols, degraded=result.degraded,
        model=result.model, pt=result.prompt_tokens, ct=result.completion_tokens,
    )


def _save(
    session: Session,
    title: str,
    body: str,
    symbols: list[str],
    *,
    degraded: bool = False,
    reason: str | None = None,
    model: str | None = None,
    pt: int | None = None,
    ct: int | None = None,
) -> InsightDocument:
    doc = InsightDocument(
        doc_type="SCREENER_REVIEW",
        market=None,
        title=title,
        body_md=body,
        degraded=degraded,
        degraded_reason=reason,
        model=model,
        prompt_tokens=pt,
        completion_tokens=ct,
        source_ref={"symbols": symbols},
    )
    session.add(doc)
    session.commit()
    session.refresh(doc)
    return doc


__all__ = ["review_hits", "build_screener_context"]
