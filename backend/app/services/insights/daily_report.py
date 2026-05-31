"""日报生成服务 —— 组装上下文 → AI 叙述 → 存文档；不可用时优雅降级。"""

from __future__ import annotations

from collections.abc import Callable
from datetime import date

from sqlmodel import Session, select

from app.config import settings
from app.logging_config import get_logger
from app.models.insight import InsightDocument, ReportConfig
from app.services.ai import client as ai_client
from app.services.ai import prompts
from app.services.ai.models import model_for
from app.services.insights.context import build_report_context, render_context_for_ai, render_context_md

log = get_logger(__name__)

DISCLAIMER = "\n\n---\n*AI 仅供参考，不构成投资建议，不预测股价、不提供买卖信号。*"

_MARKET_LABEL = {"US": "美股", "CN": "A股", "HK": "港股", "JP": "日股"}

# 进度回调：reporter(stage: str, progress: int, message: str|None) -> None
ProgressReporter = Callable[[str, int, str | None], None]


def _noop_reporter(stage: str, progress: int, message: str | None = None) -> None:  # noqa: ARG001
    """默认空进度回调（无任务跟踪时使用）。"""


def get_or_create_config(session: Session) -> ReportConfig:
    """取日报配置（单份，id=1）；不存在则用默认值创建。"""
    cfg = session.get(ReportConfig, 1)
    if cfg is not None:
        return cfg
    # 默认：启用当前已有持仓所在市场；无则默认 US
    from app.models.stock import Stock
    from app.services.analysis.pnl import compute_all_holdings

    markets = sorted({ph.stock.market for ph in compute_all_holdings(session)})
    if not markets:
        markets = ["US"]
    default_schedule = {"US": "06:30", "CN": "16:30", "HK": "17:30", "JP": "16:00"}
    cfg = ReportConfig(
        id=1,
        enabled_markets=markets,
        schedule={m: default_schedule.get(m, "18:00") for m in markets},
    )
    session.add(cfg)
    session.commit()
    session.refresh(cfg)
    return cfg


def _title(market: str, on_date: date) -> str:
    return f"{_MARKET_LABEL.get(market, market)}日报 · {on_date.isoformat()}"


def _upsert(session: Session, market: str, on_date: date, **fields) -> InsightDocument:
    """按 (DAILY_REPORT, market, report_date) 幂等写入。"""
    existing = session.exec(
        select(InsightDocument).where(
            InsightDocument.doc_type == "DAILY_REPORT",
            InsightDocument.market == market,
            InsightDocument.report_date == on_date,
        )
    ).first()
    if existing is not None:
        for k, v in fields.items():
            setattr(existing, k, v)
        existing.is_read = False
        session.add(existing)
        session.commit()
        session.refresh(existing)
        return existing
    doc = InsightDocument(
        doc_type="DAILY_REPORT",
        market=market,
        report_date=on_date,
        **fields,
    )
    session.add(doc)
    session.commit()
    session.refresh(doc)
    return doc


def build_daily_report(
    session: Session,
    market: str,
    config: ReportConfig | None = None,
    on_date: date | None = None,
    progress: ProgressReporter | None = None,
    skip_if_empty: bool = False,
) -> InsightDocument | None:
    """生成某市场日报，返回文档。失败/不可用走降级。

    progress：可选进度回调，用于向任务状态上报阶段/进度。
    skip_if_empty：True 时若当日无实质事件（异动/触价/待办）则不生成文档、返回 None
                  （事件驱动：定时任务用，避免在没内容的交易日硬产出空日报）。
    """
    report = progress or _noop_reporter
    market = market.upper()
    on_date = on_date or date.today()
    config = config or get_or_create_config(session)

    # 阶段 1：收集上下文（行情/异动/触价/待办）
    report("CONTEXT", 15, "收集行情与持仓异动")
    ctx = build_report_context(session, market, config.move_threshold_pct, on_date)
    data_md = render_context_md(ctx)
    title = _title(market, on_date)

    # C：事件驱动 —— 无实质事件时，定时任务跳过（不写空文档）
    if not ctx.has_any and skip_if_empty:
        log.info("daily_report.skipped_empty", market=market, on_date=on_date.isoformat())
        return None

    # 无重点事项 → 简短文档（仍记录；手动生成时走这里）
    if not ctx.has_any:
        report("SAVING", 90, "今日无重点事项，写入数据汇总")
        body = f"# {title}\n\n> 今日无重点事项（无超阈值异动、无触价、无待办）。\n\n{data_md}{DISCLAIMER}"
        return _upsert(
            session, market, on_date,
            title=title, body_md=body, degraded=False,
            source_ref={"config_id": config.id},
        )

    # AI 不可用 → 降级（仅机械数据）
    if not ai_client.is_available(session):
        report("SAVING", 90, "AI 未配置，写入数据汇总版")
        body = f"# {title}\n\n> （AI 未配置，本篇为数据汇总版）\n\n{data_md}{DISCLAIMER}"
        return _upsert(
            session, market, on_date,
            title=title, body_md=body, degraded=True,
            degraded_reason="AI 未配置（缺少 API Key）",
            source_ref={"config_id": config.id},
        )

    # 预算检查
    # 日报使用的服务商/模型：日报配置里指定，未指定则用全局默认服务商
    from app.services.ai import providers as ai_providers

    rp = ai_providers.resolve(
        session, provider_id=config.provider_id, model=config.model_name
    )
    model = rp.model if rp else model_for("DAILY_REPORT")
    user_prompt = prompts.render_daily_report(
        render_context_for_ai(ctx),
        market=_MARKET_LABEL.get(market, market),
        focus=config.focus_text or "",
        constraints="；".join(config.constraints or []),
        language={"zh": "简体中文", "ja": "日本語", "en": "English"}.get(config.language, "简体中文"),
        tone={"CONSERVATIVE": "保守谨慎", "NEUTRAL": "中性客观"}.get(config.tone, "中性客观"),
        detail={"BRIEF": "简洁", "STANDARD": "适中", "DETAILED": "详细"}.get(config.detail_level, "适中"),
    )

    # 阶段 2：AI 叙述生成（无预算限制）
    report("AI", 45, f"调用 AI（{model}）生成叙述")
    try:
        result = ai_client.analyze(
            session,
            prompt_type="DAILY_REPORT",
            system_prompt=prompts.SYSTEM_BASE,
            user_content=user_prompt,
            target_type="PORTFOLIO",
            target_id=None,
            max_tokens=settings.ai_analysis_max_tokens,
            force_model=config.model_name,
            provider_id=config.provider_id,
        )
    except Exception as e:  # noqa: BLE001  AI 调用异常 → 降级
        log.warning("daily_report.ai_failed", market=market, error=str(e))
        report("SAVING", 90, "AI 调用失败，写入数据汇总版")
        body = f"# {title}\n\n> （AI 调用失败，本篇为数据汇总版）\n\n{data_md}{DISCLAIMER}"
        return _upsert(
            session, market, on_date,
            title=title, body_md=body, degraded=True,
            degraded_reason=f"AI 调用失败：{e}", source_ref={"config_id": config.id},
        )

    # 阶段 3：写入文档
    report("SAVING", 90, "写入日报文档")
    # result.response 已含 DISCLAIMER；附数据明细在末尾便于核对
    body = f"# {title}\n\n{result.response}\n\n---\n\n<details>\n<summary>数据明细</summary>\n\n{data_md}\n\n</details>"
    return _upsert(
        session, market, on_date,
        title=title, body_md=body, degraded=result.degraded,
        degraded_reason=None,
        model=result.model,
        prompt_tokens=result.prompt_tokens,
        completion_tokens=result.completion_tokens,
        source_ref={"config_id": config.id},
    )


__all__ = ["build_daily_report", "get_or_create_config"]
