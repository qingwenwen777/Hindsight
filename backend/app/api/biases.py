"""认知偏差防御 API：录入前/卖出前的实时检测。"""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session

from app.core.response import ok
from app.database import get_session
from app.models.stock import Stock
from app.services.biases.cooling_period import detect_revenge_trade
from app.services.biases.holding_time import check_early_sell

router = APIRouter(prefix="/biases", tags=["biases"])


class CooldownCheckRequest(BaseModel):
    stock_id: int
    type: str  # BUY / SELL
    sell_date: date | None = None


@router.post("/cooldown-check", summary="录入前防御检测")
def cooldown_check(payload: CooldownCheckRequest, session: Session = Depends(get_session)) -> dict:
    """返回该笔交易应有的冷静期与告警。

    - BUY：检测复仇交易（连亏 3 次后买同股 → 5 分钟冷静 + AI 确认）。
    - SELL：检测持有时间警告（声明 LONG 但 < 30 天卖）。
    """
    if not session.get(Stock, payload.stock_id):
        raise HTTPException(status_code=404, detail="股票不存在")

    result: dict = {"warnings": []}
    side = payload.type.upper()

    if side == "BUY":
        decision = detect_revenge_trade(session, payload.stock_id)
        result["cooldown_seconds"] = decision.seconds
        result["is_revenge"] = decision.is_revenge
        result["require_ai_confirm"] = decision.require_ai_confirm
        if decision.is_revenge:
            result["warnings"].append(decision.reason)
    else:
        result["cooldown_seconds"] = 30
        result["is_revenge"] = False
        result["require_ai_confirm"] = False
        sell_date = payload.sell_date or date.today()
        ht = check_early_sell(session, payload.stock_id, sell_date)
        if ht.triggered:
            result["holding_time_warning"] = {
                "declared_horizon": ht.declared_horizon,
                "held_days": ht.held_days,
                "reason": ht.reason,
            }
            result["warnings"].append(ht.reason)

    return ok(result)
