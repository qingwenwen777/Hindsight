"""技术指标测试 —— 对已知数据验证首尾值与参考实现一致。"""

from __future__ import annotations

from app.services.analysis import indicators


def test_ma_known() -> None:
    """MA3 对 [1,2,3,4,5]：前两个 None，之后 [2,3,4]。"""
    result = indicators.ma([1, 2, 3, 4, 5], period=3)
    assert result[0] is None
    assert result[1] is None
    assert result[2] == 2.0
    assert result[3] == 3.0
    assert result[4] == 4.0


def test_ema_first_value_equals_first_price() -> None:
    """EMA(adjust=False) 首值等于首个价格。"""
    result = indicators.ema([10, 11, 12], period=2)
    assert result[0] == 10.0
    # 第二个：alpha=2/3 → 10 + 2/3*(11-10) = 10.6667
    assert abs(result[1] - 10.6667) < 0.001


def test_macd_converges() -> None:
    """MACD 在恒定价格序列下 DIF/DEA/hist 应趋近 0。"""
    close = [100.0] * 100
    m = indicators.macd(close)
    assert abs(m["dif"][-1]) < 1e-6
    assert abs(m["dea"][-1]) < 1e-6
    assert abs(m["hist"][-1]) < 1e-6


def test_rsi_all_gains_is_100() -> None:
    """单调上涨序列 RSI 应为 100。"""
    close = list(range(1, 30))  # 持续上涨
    r = indicators.rsi([float(x) for x in close], period=14)
    assert r[-1] == 100.0


def test_rsi_range() -> None:
    """RSI 落在 [0,100]，前 period 个为 None。"""
    close = [44, 44.34, 44.09, 44.15, 43.61, 44.33, 44.83, 45.10, 45.42, 45.84,
             46.08, 45.89, 46.03, 45.61, 46.28, 46.28]
    r = indicators.rsi(close, period=14)
    assert r[0] is None
    last = r[-1]
    assert last is not None
    assert 0 <= last <= 100


def test_bollinger_mid_equals_ma() -> None:
    """布林中轨等于同周期 MA。"""
    close = [float(x) for x in range(1, 30)]
    boll = indicators.bollinger(close, period=20)
    ma20 = indicators.ma(close, period=20)
    assert boll["mid"][-1] == ma20[-1]
    # 上轨 > 中轨 > 下轨
    assert boll["upper"][-1] > boll["mid"][-1] > boll["lower"][-1]


def test_kdj_range() -> None:
    """KDJ 计算不报错，末值有数。"""
    n = 30
    high = [float(10 + i % 5) for i in range(n)]
    low = [float(8 + i % 3) for i in range(n)]
    close = [float(9 + i % 4) for i in range(n)]
    k = indicators.kdj(high, low, close)
    assert k["k"][-1] is not None
    assert k["d"][-1] is not None
    assert k["j"][-1] is not None


def test_compute_indicators_selective() -> None:
    """按 types 选择性计算。"""
    close = [float(x) for x in range(1, 70)]
    out = indicators.compute_indicators(close, types=["MA", "RSI"])
    assert "ma" in out
    assert "rsi" in out
    assert "macd" not in out
