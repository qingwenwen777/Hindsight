"""AI 月度预算守卫（设计文档 5.5）。"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from sqlmodel import Session, select

from app.config import settings
from app.core.money import D
from app.models.ai_insight import AiInsight

ZERO = Decimal("0")


class BudgetExceeded(Exception):
    """超出月度预算。"""


class BudgetGuard:
    """月度硬上限守卫。"""

    def __init__(self, session: Session, monthly_budget_jpy: int | None = None) -> None:
        self.session = session
        self.monthly_budget_jpy = Decimal(
            monthly_budget_jpy if monthly_budget_jpy is not None else settings.ai_monthly_budget_jpy
        )

    def _month_start(self) -> datetime:
        now = datetime.now(timezone.utc)
        return datetime(now.year, now.month, 1, tzinfo=timezone.utc)

    def used_this_month(self) -> Decimal:
        """本月已用（JPY），从 ai_insights.cost_jpy 累加。"""
        start = self._month_start()
        rows = self.session.exec(
            select(AiInsight.cost_jpy).where(AiInsight.created_at >= start)
        ).all()
        total = ZERO
        for c in rows:
            if c is not None:
                total += D(c)
        return total

    def remaining(self) -> Decimal:
        return self.monthly_budget_jpy - self.used_this_month()

    def can_call(self, estimated_cost: Decimal) -> bool:
        return self.used_this_month() + estimated_cost <= self.monthly_budget_jpy

    def ensure(self, estimated_cost: Decimal) -> None:
        """超限则抛 BudgetExceeded。"""
        if not self.can_call(estimated_cost):
            raise BudgetExceeded(
                f"AI 月度预算 {self.monthly_budget_jpy} JPY 不足：已用 "
                f"{self.used_this_month():.2f}，本次预估 {estimated_cost:.2f}"
            )

    def usage_ratio(self) -> float:
        if self.monthly_budget_jpy == ZERO:
            return 1.0
        return float(self.used_this_month() / self.monthly_budget_jpy)

    def is_close(self, threshold: float = 0.8) -> bool:
        return self.usage_ratio() >= threshold
