"""手续费引擎（设计文档 7.3）。

按市场 / 方向 / 成交额计算佣金、印花税、规费等。
所有金额用 Decimal；费率版本化由 fee_rules 表承载（按交易日匹配生效规则）。

预置规则（无 DB 规则时的兜底默认值）：
- A 股 BUY:  佣金 0.025%（最低 5 CNY）
- A 股 SELL: 佣金 0.025% + 印花税 0.05% + 过户费 0.001%
- 港股:      佣金 0.0027% + 印花税 0.13% + 交易征费 0.0027%
- 美股 BUY:  佣金 0（IBKR 阶梯）或 1 USD（富途）—— 默认按 0 计佣，SELL 另加 SEC/FINRA
- 美股 SELL: 佣金 + SEC fee 0.00229% + FINRA 每股 0.000166
- 日股:      楽天証券默认 0.099%（含消费税）
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from sqlmodel import Session, select

from app.core.money import D, quantize_money
from app.models.fee_rule import FeeRule


@dataclass
class Fees:
    """费用明细。total = commission + tax + other_fees。"""

    commission: Decimal = field(default_factory=lambda: Decimal("0"))
    tax: Decimal = field(default_factory=lambda: Decimal("0"))
    other_fees: Decimal = field(default_factory=lambda: Decimal("0"))

    @property
    def total(self) -> Decimal:
        return self.commission + self.tax + self.other_fees

    def quantized(self) -> "Fees":
        """按货币精度量化（展示用）。"""
        return Fees(
            commission=quantize_money(self.commission),
            tax=quantize_money(self.tax),
            other_fees=quantize_money(self.other_fees),
        )


# ---- 预置默认费率（DB 无规则时兜底）----
# 单位：rate 为比率（0.00025 = 0.025%），min_amount 为最低佣金，per_share 为每股固定。
_DEFAULT_RULES: dict[str, dict] = {
    "CN": {
        "commission_rate": D("0.00025"),
        "commission_min": D("5"),
        "stamp_rate_sell": D("0.0005"),  # 印花税仅卖出
        "transfer_rate": D("0.00001"),  # 过户费双向
    },
    "HK": {
        "commission_rate": D("0.000027"),
        "commission_min": D("0"),
        "stamp_rate": D("0.0013"),  # 印花税双向
        "levy_rate": D("0.000027"),  # 交易征费双向
    },
    "US": {
        "commission_rate": D("0"),  # 默认零佣
        "commission_min": D("0"),
        "sec_rate_sell": D("0.0000229"),  # SEC fee 仅卖出
        "finra_per_share_sell": D("0.000166"),  # FINRA 每股，仅卖出
    },
    "JP": {
        "commission_rate": D("0.00099"),  # 楽天証券默认含消费税
        "commission_min": D("0"),
    },
}


def _calc_from_defaults(
    market: str,
    direction: str,
    amount: Decimal,
    quantity: Decimal,
) -> Fees:
    """用预置默认费率计算（无 DB 规则时）。"""
    market = market.upper()
    direction = direction.upper()
    rules = _DEFAULT_RULES.get(market)
    if rules is None:
        return Fees()

    fees = Fees()
    # 佣金
    comm_rate = rules.get("commission_rate", D("0"))
    comm_min = rules.get("commission_min", D("0"))
    commission = amount * comm_rate
    if comm_min and commission < comm_min:
        commission = comm_min
    fees.commission = commission

    if market == "CN":
        if direction == "SELL":
            fees.tax = amount * rules["stamp_rate_sell"]
        # 过户费双向
        fees.other_fees += amount * rules["transfer_rate"]
    elif market == "HK":
        # 印花税与交易征费双向
        fees.tax = amount * rules["stamp_rate"]
        fees.other_fees += amount * rules["levy_rate"]
    elif market == "US":
        if direction == "SELL":
            fees.other_fees += amount * rules["sec_rate_sell"]
            fees.other_fees += quantity * rules["finra_per_share_sell"]
    # JP 仅佣金

    return fees


def _select_best_rule(rules: list[FeeRule], broker: str | None, trade_date: date | None) -> FeeRule:
    """在同一 fee_type 的多条候选规则里挑唯一一条，避免区间重叠重复计费。

    优先级：
      1. broker 精确匹配优先于通配规则；
      2. effective_from 较晚（更新版本）优先；
      3. effective_to 较晚（更长有效）优先。
    """
    def _key(r: FeeRule) -> tuple:
        broker_match = 1 if (broker and r.broker == broker) else 0
        eff_from = r.effective_from or date.min
        eff_to = r.effective_to or date.max
        return (broker_match, eff_from, eff_to)

    return max(rules, key=_key)


def _calc_from_db_rules(
    rules: list[FeeRule], amount: Decimal, quantity: Decimal
) -> tuple[Fees, set[str]]:
    """用 DB 中匹配到的版本化规则计算。

    fee_type 语义：
      COMMISSION → 计入 commission（rate*amount，受 min/fixed 约束）
      STAMP / TAX → 计入 tax
      其他（SEC_FEE/FINRA/TRANSFER/LEVY…）→ 计入 other_fees
    per_share 优先于 rate（用于 FINRA 每股费）。

    返回 (Fees, 覆盖的类别集合)。类别为 {"commission","tax","other_fees"}，
    供上层判断哪些类别需要回退默认值。
    同一 fee_type 若有多条规则（如区间重叠），只取最匹配的一条，杜绝重复计费。
    """
    # 按 fee_type 分组，每组只保留一条最匹配规则
    by_type: dict[str, list[FeeRule]] = {}
    for r in rules:
        by_type.setdefault(r.fee_type.upper(), []).append(r)

    fees = Fees()
    covered: set[str] = set()
    for ft, group in by_type.items():
        r = group[0] if len(group) == 1 else _select_best_rule(group, None, None)
        if r.per_share is not None:
            amt = quantity * r.per_share
        elif r.fixed_amount is not None:
            amt = r.fixed_amount
        elif r.rate is not None:
            amt = amount * r.rate
        else:
            amt = Decimal("0")
        if r.min_amount is not None and amt < r.min_amount:
            amt = r.min_amount

        if ft == "COMMISSION":
            fees.commission += amt
            covered.add("commission")
        elif ft in ("STAMP", "TAX"):
            fees.tax += amt
            covered.add("tax")
        else:
            fees.other_fees += amt
            covered.add("other_fees")
    return fees, covered


def calculate_fees(
    market: str,
    direction: str,
    amount: Decimal | str | int,
    quantity: Decimal | str | int = Decimal("0"),
    *,
    broker: str | None = None,
    trade_date: date | None = None,
    session: Session | None = None,
) -> Fees:
    """计算手续费。

    - 优先用 DB 中按 (market, broker, direction, trade_date) 匹配的版本化规则。
    - 无匹配规则时回退到预置默认费率。
    - amount：成交额（price * quantity，原币种）。
    - quantity：股数（用于每股固定费，如 FINRA）。
    """
    amount = D(amount)
    quantity = D(quantity)
    direction = direction.upper()

    if session is not None:
        stmt = select(FeeRule).where(FeeRule.market == market.upper())
        if trade_date is not None:
            stmt = stmt.where(FeeRule.effective_from <= trade_date)
        db_rules = list(session.exec(stmt).all())
        # 过滤：方向匹配（BOTH 或 None 视为通配）、broker 匹配、生效区间
        matched: list[FeeRule] = []
        for r in db_rules:
            if r.direction and r.direction.upper() not in (direction, "BOTH"):
                continue
            if r.broker and broker and r.broker != broker:
                continue
            if r.broker and not broker:
                continue
            if trade_date and r.effective_to and r.effective_to < trade_date:
                continue
            matched.append(r)
        if matched:
            db_fees, covered = _calc_from_db_rules(matched, amount, quantity)
            # 部分配置回退：DB 只配了某些类别（如仅 COMMISSION）时，
            # 未配置的类别（印花税/过户费等）回退到预置默认，避免漏费。
            defaults = _calc_from_defaults(market, direction, amount, quantity)
            merged = Fees(
                commission=db_fees.commission if "commission" in covered else defaults.commission,
                tax=db_fees.tax if "tax" in covered else defaults.tax,
                other_fees=db_fees.other_fees if "other_fees" in covered else defaults.other_fees,
            )
            return merged

    return _calc_from_defaults(market, direction, amount, quantity)
