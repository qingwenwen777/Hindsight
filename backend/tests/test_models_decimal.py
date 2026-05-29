"""验证 Decimal-as-TEXT 模型存取无浮点误差。"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlmodel import Session, SQLModel, create_engine, select

from app.models import Price, Stock, Transaction


def _make_engine():
    """内存 SQLite 引擎 + 建表。"""
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)
    return engine


def test_decimal_round_trip_no_float_error() -> None:
    """插入一个有大量小数位的金额，读回必须逐位精确。"""
    engine = _make_engine()
    # 0.1 + 0.2 在 float 下会变 0.30000000000000004，这里用 Decimal 累加验证精确
    tricky = Decimal("0.1") + Decimal("0.2")
    assert tricky == Decimal("0.3")

    with Session(engine) as s:
        stock = Stock(symbol="600519", market="CN", name="贵州茅台", currency="CNY")
        s.add(stock)
        s.commit()
        s.refresh(stock)

        tx = Transaction(
            stock_id=stock.id,
            type="BUY",
            trade_date=date(2026, 1, 2),
            quantity=Decimal("100"),
            price=Decimal("1688.88"),
            currency="CNY",
            commission=Decimal("4.2222"),
        )
        s.add(tx)
        s.commit()
        s.refresh(tx)

    with Session(engine) as s:
        got = s.exec(select(Transaction)).one()
        # 逐位精确：price 与 commission 不丢精度
        assert got.price == Decimal("1688.88")
        assert got.commission == Decimal("4.2222")
        # 类型必须是 Decimal，不是 float
        assert isinstance(got.price, Decimal)
        assert isinstance(got.commission, Decimal)
        # 成交额精确
        assert got.price * got.quantity == Decimal("168888.00")


def test_price_high_precision() -> None:
    """价格高精度（adjust_factor 多位小数）存取精确。"""
    engine = _make_engine()
    with Session(engine) as s:
        stock = Stock(symbol="AAPL", market="US", name="Apple", currency="USD")
        s.add(stock)
        s.commit()
        s.refresh(stock)

        p = Price(
            stock_id=stock.id,
            date=date(2026, 5, 28),
            open=Decimal("310.679993"),
            high=Decimal("312.799988"),
            low=Decimal("309.570007"),
            close=Decimal("312.510010"),
            volume=48157800,
            adjust_factor=Decimal("0.9987654321"),
        )
        s.add(p)
        s.commit()

    with Session(engine) as s:
        got = s.exec(select(Price)).one()
        assert got.close == Decimal("312.510010")
        assert got.adjust_factor == Decimal("0.9987654321")
        assert got.volume == 48157800
