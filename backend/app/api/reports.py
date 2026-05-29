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


def _serialize_period(r) -> dict:  # noqa: ANN001
    return {
        "period": r.period,
        "start": r.start.isoformat(),
        "end": r.end.isoformat(),
        "buy_count": r.buy_count,
        "sell_count": r.sell_count,
        "total_buy_amount": to_db_str(r.total_buy_amount),
        "total_sell_amount": to_db_str(r.total_sell_amount),
        "total_fees": to_db_str(r.total_fees),
        "symbols_traded": r.symbols_traded,
    }


@router.get("/monthly", summary="月度报表")
def monthly_report(
    year: int = Query(...),
    month: int = Query(..., ge=1, le=12),
    session: Session = Depends(get_session),
) -> dict:
    from app.services.analysis.reports import build_period_report

    return ok(_serialize_period(build_period_report(session, year, month=month)))


@router.get("/quarterly", summary="季度报表")
def quarterly_report(
    year: int = Query(...),
    quarter: int = Query(..., ge=1, le=4),
    session: Session = Depends(get_session),
) -> dict:
    from app.services.analysis.reports import build_period_report

    return ok(_serialize_period(build_period_report(session, year, quarter=quarter)))


@router.get("/yearly", summary="年度报表")
def yearly_report(year: int = Query(...), session: Session = Depends(get_session)) -> dict:
    from app.services.analysis.reports import build_period_report

    return ok(_serialize_period(build_period_report(session, year)))


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
