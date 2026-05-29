"""AI 模型分级与定价（设计文档 5.5）。

模型分级：摘要/标签用 Haiku（便宜），复盘/魔鬼代言人/失败模式用 Sonnet。
价格用于成本估算与预算控制；以 USD/百万 token 计，换算为 JPY。
"""

from __future__ import annotations

from decimal import Decimal

# Anthropic 模型 ID（可在 .env / 设置里覆盖具体版本）
HAIKU = "claude-3-5-haiku-latest"
SONNET = "claude-sonnet-4-5"
OPUS = "claude-opus-4-1"

# 任务 → 模型分级（设计文档 5.5）
TASK_MODEL_MAP: dict[str, str] = {
    "EARNINGS_SUMMARY": HAIKU,
    "TAG_GENERATION": HAIKU,
    "TRADE_REVIEW": SONNET,
    "PEER_COMPARE": SONNET,
    "DEVILS_ADVOCATE": SONNET,
    "FAILURE_PATTERN": SONNET,  # v1.1 由 Opus 降级控成本
    "QUARTERLY_REVIEW": SONNET,
    "CHAT": SONNET,
}

# 模型定价（USD / 百万 token），(input, output)。用于成本估算。
MODEL_PRICING_USD: dict[str, tuple[Decimal, Decimal]] = {
    HAIKU: (Decimal("0.80"), Decimal("4.00")),
    SONNET: (Decimal("3.00"), Decimal("15.00")),
    OPUS: (Decimal("15.00"), Decimal("75.00")),
}

# 估算用汇率（USD->JPY），可被实时汇率覆盖
DEFAULT_USD_JPY = Decimal("150")


def model_for(prompt_type: str) -> str:
    """按任务类型选模型，未知默认 Sonnet。"""
    return TASK_MODEL_MAP.get(prompt_type.upper(), SONNET)


def estimate_cost_jpy(
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
    usd_jpy: Decimal = DEFAULT_USD_JPY,
) -> Decimal:
    """根据 token 数估算成本（JPY）。"""
    pricing = MODEL_PRICING_USD.get(model, MODEL_PRICING_USD[SONNET])
    in_price, out_price = pricing
    cost_usd = (
        Decimal(prompt_tokens) / Decimal("1000000") * in_price
        + Decimal(completion_tokens) / Decimal("1000000") * out_price
    )
    return cost_usd * usd_jpy
