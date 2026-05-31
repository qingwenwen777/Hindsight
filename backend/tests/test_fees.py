"""手续费引擎单元测试 —— 含手算可验证样例。"""

from __future__ import annotations

from decimal import Decimal

from app.core.fees import calculate_fees


def test_cn_buy_commission_min() -> None:
    """A 股买入，小额触发最低佣金 5 CNY。

    成交额 1000 CNY × 0.025% = 0.25 < 5 → 佣金取 5。
    过户费 1000 × 0.001% = 0.01。买入无印花税。
    """
    fees = calculate_fees("CN", "BUY", amount="1000", quantity="100").quantized()
    assert fees.commission == Decimal("5.00")
    assert fees.tax == Decimal("0.00")
    assert fees.other_fees == Decimal("0.01")
    assert fees.total == Decimal("5.01")


def test_cn_buy_commission_normal() -> None:
    """A 股买入，大额按比例计佣。

    成交额 100000 × 0.025% = 25（> 5，不触发最低）。
    过户费 100000 × 0.001% = 1.00。无印花税。
    """
    fees = calculate_fees("CN", "BUY", amount="100000", quantity="1000").quantized()
    assert fees.commission == Decimal("25.00")
    assert fees.tax == Decimal("0.00")
    assert fees.other_fees == Decimal("1.00")
    assert fees.total == Decimal("26.00")


def test_cn_sell_with_stamp() -> None:
    """A 股卖出：佣金 + 印花税 + 过户费。

    成交额 100000：
      佣金 100000 × 0.025% = 25
      印花税 100000 × 0.05% = 50
      过户费 100000 × 0.001% = 1
      合计 76
    """
    fees = calculate_fees("CN", "SELL", amount="100000", quantity="1000").quantized()
    assert fees.commission == Decimal("25.00")
    assert fees.tax == Decimal("50.00")
    assert fees.other_fees == Decimal("1.00")
    assert fees.total == Decimal("76.00")


def test_us_sell_sec_and_finra() -> None:
    """美股卖出：零佣 + SEC fee + FINRA 每股费。

    成交额 10000 USD，数量 100 股：
      佣金 0
      SEC  10000 × 0.00229% = 0.229
      FINRA 100 × 0.000166 = 0.0166
      other_fees = 0.229 + 0.0166 = 0.2456 → 量化 0.25
    """
    fees = calculate_fees("US", "SELL", amount="10000", quantity="100")
    # 量化前精确值
    assert fees.commission == Decimal("0")
    assert fees.other_fees == Decimal("0.2456")
    q = fees.quantized()
    assert q.other_fees == Decimal("0.25")
    assert q.total == Decimal("0.25")


def test_us_buy_zero_commission() -> None:
    """美股买入默认零佣、无额外费。"""
    fees = calculate_fees("US", "BUY", amount="10000", quantity="100").quantized()
    assert fees.total == Decimal("0.00")


def test_no_float_anywhere() -> None:
    """所有返回字段必须是 Decimal，杜绝 float。"""
    fees = calculate_fees("HK", "SELL", amount="50000", quantity="500")
    assert isinstance(fees.commission, Decimal)
    assert isinstance(fees.tax, Decimal)
    assert isinstance(fees.other_fees, Decimal)


def test_db_rules_no_duplicate_for_overlapping(session) -> None:  # noqa: ANN001
    """同 fee_type 多条规则（区间重叠）只取一条，不重复计费。"""
    from datetime import date

    from app.models.fee_rule import FeeRule

    # 两条 CN COMMISSION 规则区间重叠，费率不同
    session.add(
        FeeRule(
            market="CN",
            direction="BOTH",
            fee_type="COMMISSION",
            rate=Decimal("0.0003"),
            effective_from=date(2020, 1, 1),
        )
    )
    session.add(
        FeeRule(
            market="CN",
            direction="BOTH",
            fee_type="COMMISSION",
            rate=Decimal("0.0002"),
            effective_from=date(2024, 1, 1),
        )
    )
    session.commit()

    fees = calculate_fees(
        "CN", "BUY", amount="100000", quantity="1000",
        trade_date=date(2026, 1, 1), session=session,
    )
    # 只应取较新的一条（0.0002），佣金 = 100000 * 0.0002 = 20，而不是 20+30=50
    assert fees.commission == Decimal("20")


def test_db_rules_fallback_for_uncovered_types(session) -> None:  # noqa: ANN001
    """DB 只配了佣金时，印花税/过户费回退默认，不漏费（CN SELL）。"""
    from datetime import date

    from app.models.fee_rule import FeeRule

    session.add(
        FeeRule(
            market="CN",
            direction="BOTH",
            fee_type="COMMISSION",
            rate=Decimal("0.0002"),
            effective_from=date(2020, 1, 1),
        )
    )
    session.commit()

    fees = calculate_fees(
        "CN", "SELL", amount="100000", quantity="1000",
        trade_date=date(2026, 1, 1), session=session,
    ).quantized()
    # 佣金用 DB 规则：100000 * 0.0002 = 20
    assert fees.commission == Decimal("20.00")
    # 印花税回退默认：100000 * 0.05% = 50
    assert fees.tax == Decimal("50.00")
    # 过户费回退默认：100000 * 0.001% = 1
    assert fees.other_fees == Decimal("1.00")
