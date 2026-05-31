"""报表 API：情绪审计（Step 5.3）等。"""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session

from app.core.money import to_db_str
from app.core.response import Meta, ok
from app.database import get_session
from app.services.biases.emotion_audit import audit_emotions

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/emotion-audit", summary="情绪审计")
def emotion_audit(
    start: date | None = Query(None),
    end: date | None = Query(None),
    session: Session = Depends(get_session),
) -> dict:
    """按情绪分组的胜率/平均回报/盈亏比 + 结论文案。"""
    stats = audit_emotions(session, start, end)
    data = []
    conclusions: list[str] = []
    for st in stats:
        data.append(
            {
                "emotion": st.emotion,
                "samples": st.n,
                "wins": st.wins,
                "win_rate": round(st.win_rate, 4),
                "win_rate_pct": round(st.win_rate * 100, 1),
                "avg_return_pct": to_db_str(st.avg_return),
                "profit_loss_ratio": st.profit_loss_ratio,
            }
        )
        # 结论文案：低胜率情绪提醒
        if st.n >= 3 and st.win_rate < 0.4:
            conclusions.append(
                f"{st.emotion} 状态下胜率仅 {st.win_rate * 100:.0f}%（{st.n} 笔），警惕该情绪下决策。"
            )
    return ok({"by_emotion": data, "conclusions": conclusions})


@router.get("/decision-calibration", summary="信心校准度")
def decision_calibration(
    start: date | None = Query(None),
    end: date | None = Query(None),
    session: Session = Depends(get_session),
) -> dict:
    """按录入信心(1-5)对比"主观隐含胜率" vs "实际胜率"，揭示过度自信/信心不足。"""
    from app.services.biases.decision_audit import confidence_calibration

    rows, conclusions = confidence_calibration(session, start, end)
    data = [
        {
            "confidence": r.confidence,
            "implied_win_rate": round(r.implied_win_rate, 4),
            "implied_win_rate_pct": round(r.implied_win_rate * 100, 1),
            "actual_win_rate": round(r.actual_win_rate, 4),
            "actual_win_rate_pct": round(r.actual_win_rate * 100, 1),
            "samples": r.n,
            "avg_return_pct": to_db_str(r.avg_return),
            "gap_pct": round(r.gap * 100, 1),
        }
        for r in rows
    ]
    return ok({"by_confidence": data, "conclusions": conclusions})


@router.get("/decision-categories", summary="决策类别聚合")
def decision_categories(
    start: date | None = Query(None),
    end: date | None = Query(None),
    session: Session = Depends(get_session),
) -> dict:
    """按论点类别(价值/趋势/事件/成长)统计胜率/平均回报/盈亏比。"""
    from app.services.biases.decision_audit import category_aggregation

    rows, conclusions = category_aggregation(session, start, end)
    data = [
        {
            "category": r.key,
            "samples": r.n,
            "wins": r.wins,
            "win_rate": round(r.win_rate, 4),
            "win_rate_pct": round(r.win_rate * 100, 1),
            "avg_return_pct": to_db_str(r.avg_return),
            "profit_loss_ratio": r.profit_loss_ratio,
        }
        for r in rows
    ]
    return ok({"by_category": data, "conclusions": conclusions})


def _serialize_period(r) -> dict:  # noqa: ANN001
    return {
        "period": r.period,
        "start": r.start.isoformat(),
        "end": r.end.isoformat(),
        "currency": r.currency,
        "buy_count": r.buy_count,
        "sell_count": r.sell_count,
        "total_buy_amount": to_db_str(r.total_buy_amount),
        "total_sell_amount": to_db_str(r.total_sell_amount),
        "total_fees": to_db_str(r.total_fees),
        "symbols_traded": r.symbols_traded,
        "is_estimated": r.is_estimated,
    }


def _ensure_fx(session: Session) -> None:
    """报表跨币种换算前，确保当天有汇率（无则联网拉取，失败回退历史）。"""
    from datetime import date as _date

    from app.services.data_sync.fx_client import has_rates_for_date, store_live_rates

    if not has_rates_for_date(session, _date.today()):
        try:
            store_live_rates(session, _date.today())
        except Exception:  # noqa: BLE001, S110
            pass


@router.get("/monthly", summary="月度报表")
def monthly_report(
    year: int = Query(...),
    month: int = Query(..., ge=1, le=12),
    currency: str = Query("JPY", description="换算目标币种 JPY/USD/CNY/HKD"),
    session: Session = Depends(get_session),
) -> dict:
    from app.services.analysis.reports import build_period_report

    _ensure_fx(session)
    return ok(_serialize_period(build_period_report(session, year, month=month, currency=currency)))


@router.get("/quarterly", summary="季度报表")
def quarterly_report(
    year: int = Query(...),
    quarter: int = Query(..., ge=1, le=4),
    currency: str = Query("JPY", description="换算目标币种 JPY/USD/CNY/HKD"),
    session: Session = Depends(get_session),
) -> dict:
    from app.services.analysis.reports import build_period_report

    _ensure_fx(session)
    return ok(_serialize_period(build_period_report(session, year, quarter=quarter, currency=currency)))


@router.get("/yearly", summary="年度报表")
def yearly_report(
    year: int = Query(...),
    currency: str = Query("JPY", description="换算目标币种 JPY/USD/CNY/HKD"),
    session: Session = Depends(get_session),
) -> dict:
    from app.services.analysis.reports import build_period_report

    _ensure_fx(session)
    return ok(_serialize_period(build_period_report(session, year, currency=currency)))


@router.get("/failures", summary="失败案例库")
def failures(session: Session = Depends(get_session)) -> dict:
    """买入后 30 天亏损 > 5% 的交易聚合。"""
    from app.services.analysis.reports import build_failure_library

    cases = build_failure_library(session)
    data = [
        {
            "transaction_id": c.transaction_id,
            "symbol": c.symbol,
            "name": c.name,
            "trade_date": c.trade_date,
            "return_30d_pct": to_db_str(c.return_30d),
            "emotion": c.emotion,
            "thesis": c.thesis,
        }
        for c in cases
    ]
    return ok(data, meta=Meta(total=len(data)))


@router.get("/review-reminders", summary="复盘到期提醒")
def review_reminders(session: Session = Depends(get_session)) -> dict:
    """距决策 30/60/90/180/365 天且未复盘的日志提醒。"""
    from app.services.analysis.reminders import compute_reminders

    items = compute_reminders(session)
    data = [
        {
            "journal_id": r.journal_id,
            "stock_id": r.stock_id,
            "symbol": r.symbol,
            "name": r.name,
            "decision_type": r.decision_type,
            "decision_date": r.decision_date,
            "days_since": r.days_since,
            "due_milestone": r.due_milestone,
            "overdue_days": r.overdue_days,
        }
        for r in items
    ]
    return ok(data, meta=Meta(total=len(data)))
