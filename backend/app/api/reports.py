"""报表 API：情绪审计（Step 5.3）等。"""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session

from app.core.money import to_db_str
from app.core.response import ok
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
