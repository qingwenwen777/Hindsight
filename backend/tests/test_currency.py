"""多币种换算测试：直接/反向/中转/最近日回退/估算标记。"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from sqlmodel import Session

from app.core.currency import FxRateUnavailable, convert, get_fx_quote
from app.core.money import Money
from app.services.data_sync.fx_client import upsert_fx_rate


def test_same_currency_is_identity(session: Session) -> None:
    q = get_fx_quote(session, "JPY", "JPY", date(2026, 5, 1))
    assert q.rate == Decimal("1")
    assert q.is_estimated is False


def test_direct_rate(session: Session) -> None:
    """USD->JPY 直接汇率。"""
    upsert_fx_rate(session, "USD", "JPY", date(2026, 5, 1), "150")
    q = get_fx_quote(session, "USD", "JPY", date(2026, 5, 1))
    assert q.rate == Decimal("150")
    assert q.is_estimated is False
    # 100 USD -> 15000 JPY
    m = convert(session, Money("100", "USD"), "JPY", date(2026, 5, 1))
    assert m.amount == Decimal("15000")
    assert m.currency == "JPY"


def test_nearest_date_fallback_is_estimated(session: Session) -> None:
    """查询日无汇率时回退最近一天，标记估算。"""
    upsert_fx_rate(session, "USD", "JPY", date(2026, 5, 1), "150")
    # 查 5/3，没有当天，回退 5/1
    q = get_fx_quote(session, "USD", "JPY", date(2026, 5, 3))
    assert q.rate == Decimal("150")
    assert q.is_estimated is True
    assert q.rate_date == date(2026, 5, 1)


def test_inverse_rate(session: Session) -> None:
    """只有 USD->JPY，查 JPY->USD 取倒数。"""
    upsert_fx_rate(session, "USD", "JPY", date(2026, 5, 1), "150")
    q = get_fx_quote(session, "JPY", "USD", date(2026, 5, 1))
    assert q.rate == Decimal("1") / Decimal("150")
    assert q.is_estimated is True


def test_triangulation_via_jpy(session: Session) -> None:
    """无 USD->CNY，但有 USD->JPY 和 CNY->JPY，经 JPY 中转。

    USD->JPY=150，CNY->JPY=20 → JPY->CNY=1/20
    USD->CNY = 150 * (1/20) = 7.5
    """
    upsert_fx_rate(session, "USD", "JPY", date(2026, 5, 1), "150")
    upsert_fx_rate(session, "CNY", "JPY", date(2026, 5, 1), "20")
    q = get_fx_quote(session, "USD", "CNY", date(2026, 5, 1))
    assert q.rate == Decimal("150") * (Decimal("1") / Decimal("20"))
    assert q.is_estimated is True


def test_unavailable_raises(session: Session) -> None:
    with pytest.raises(FxRateUnavailable):
        get_fx_quote(session, "USD", "CNY", date(2026, 5, 1))
