"""AI 客户端/预算测试：无 key 降级、预算超限拦截、缓存命中不扣费。"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pytest
from sqlmodel import Session, select

from app.models.ai_insight import AiInsight
from app.services.ai import client as ai_client
from app.services.ai.budget import BudgetExceeded, BudgetGuard
from app.services.ai.models import estimate_cost_jpy, model_for


def test_model_tiering() -> None:
    assert model_for("EARNINGS_SUMMARY").startswith("claude-3-5-haiku")
    assert "sonnet" in model_for("TRADE_REVIEW")
    assert "sonnet" in model_for("UNKNOWN_TASK")  # 默认 Sonnet


def test_cost_estimate_positive() -> None:
    cost = estimate_cost_jpy(model_for("TRADE_REVIEW"), 1000, 500)
    assert cost > 0


def test_degraded_without_key(session: Session, monkeypatch) -> None:  # noqa: ANN001
    """无服务商 → 优雅降级，不崩溃，返回带声明的提示。"""
    from app.services.ai import providers

    monkeypatch.setattr(providers, "resolve", lambda *a, **k: None)
    result = ai_client.analyze(
        session,
        prompt_type="TRADE_REVIEW",
        system_prompt="你是教练",
        user_content="一些上下文",
        target_type="TRANSACTION",
        target_id=1,
    )
    assert result.degraded is True
    assert result.cost_jpy == Decimal("0")
    assert "仅供参考" in result.response


def test_budget_exceeded(session: Session) -> None:
    """已用接近上限时拦截。"""
    # 预置一条本月 1999 JPY 的消费记录（默认预算 2000）
    session.add(
        AiInsight(
            target_type="TRANSACTION",
            target_id=1,
            prompt_type="TRADE_REVIEW",
            input_hash="x",
            model="claude-sonnet-4-5",
            cost_jpy=Decimal("1999"),
            response="prev",
            created_at=datetime.now(timezone.utc),
        )
    )
    session.commit()

    guard = BudgetGuard(session, monthly_budget_jpy=2000)
    assert guard.used_this_month() == Decimal("1999")
    with pytest.raises(BudgetExceeded):
        guard.ensure(Decimal("50"))  # 1999+50 > 2000


def test_cache_hit_no_charge(session: Session, monkeypatch) -> None:  # noqa: ANN001
    """缓存命中直接返回，不再调用模型、不扣费。"""
    from app.services.ai import providers
    from app.services.ai.providers import ResolvedProvider

    # 解析到一个内置计价模型（与缓存里 model 一致，确保 hash 命中）
    rp = ResolvedProvider(
        protocol="anthropic", base_url=None, api_key="k",
        model="claude-sonnet-4-5", provider_id=None, provider_name="test",
    )
    monkeypatch.setattr(providers, "resolve", lambda *a, **k: rp)

    # 预置缓存（hash 含模型）
    ctx = "复盘上下文 ABC"
    h = ai_client.compute_hash("TRADE_REVIEW", "claude-sonnet-4-5", ctx)
    session.add(
        AiInsight(
            target_type="TRANSACTION",
            target_id=7,
            prompt_type="TRADE_REVIEW",
            input_hash=h,
            model="claude-sonnet-4-5",
            cost_jpy=Decimal("3.5"),
            response="缓存的复盘结论",
        )
    )
    session.commit()

    result = ai_client.analyze(
        session,
        prompt_type="TRADE_REVIEW",
        system_prompt="sys",
        user_content=ctx,
        target_type="TRANSACTION",
        target_id=7,
    )
    assert result.cached is True
    assert result.response == "缓存的复盘结论"
    # 不应新增 insight 行（仍只有 1 条）
    count = len(session.exec(select(AiInsight)).all())
    assert count == 1
