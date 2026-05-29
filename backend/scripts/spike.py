"""数据源 / AI 连通性验证脚本（一次性 spike）。

验证三件事，任意一项缺依赖/缺凭据/网络受限都优雅跳过并提示：
1. AKShare 拉一只 A 股日线（贵州茅台 600519）
2. yfinance 拉一只美股日线（AAPL）
3. Anthropic 跑一个最小财报摘要（无 ANTHROPIC_API_KEY 时跳过）

用法（已激活 venv）：
    python -m scripts.spike

注意：本脚本依赖重型数据包（akshare/yfinance/anthropic）。
若未安装，会打印安装提示而非崩溃。
"""

from __future__ import annotations

import sys
from datetime import UTC, datetime, timedelta


def _section(title: str) -> None:
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def check_akshare() -> bool:
    """AKShare 拉 A 股日线。"""
    _section("1) AKShare — A 股日线 (600519 贵州茅台)")
    try:
        import akshare as ak
    except ImportError:
        print("  [跳过] 未安装 akshare。安装：pip install akshare")
        return False
    try:
        df = ak.stock_zh_a_hist(
            symbol="600519",
            period="daily",
            adjust="qfq",
        )
        if df is None or df.empty:
            print("  [警告] 返回为空，可能数据源限流或网络受限。")
            return False
        print(f"  [成功] 拉到 {len(df)} 行，列：{list(df.columns)[:6]} ...")
        print(df.tail(3).to_string(index=False))
        return True
    except Exception as e:  # noqa: BLE001
        print(f"  [失败] AKShare 调用异常（网络/数据源问题）：{type(e).__name__}: {e}")
        return False


def check_yfinance() -> bool:
    """yfinance 拉美股日线。"""
    _section("2) yfinance — 美股日线 (AAPL)")
    try:
        import yfinance as yf
    except ImportError:
        print("  [跳过] 未安装 yfinance。安装：pip install yfinance")
        return False
    try:
        end = datetime.now(UTC).date()
        start = end - timedelta(days=30)
        df = yf.download("AAPL", start=start.isoformat(), end=end.isoformat(), progress=False)
        if df is None or df.empty:
            print("  [警告] 返回为空，可能网络受限或被限流。")
            return False
        print(f"  [成功] 拉到 {len(df)} 行")
        print(df.tail(3).to_string())
        return True
    except Exception as e:  # noqa: BLE001
        print(f"  [失败] yfinance 调用异常（网络问题）：{type(e).__name__}: {e}")
        return False


def check_anthropic() -> bool:
    """Anthropic 最小财报摘要（无 key 时跳过）。"""
    _section("3) Anthropic — 最小财报摘要")
    import os

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("  [跳过] 未设置 ANTHROPIC_API_KEY，AI 部分优雅跳过（这是正常的）。")
        return False
    try:
        import anthropic
    except ImportError:
        print("  [跳过] 未安装 anthropic。安装：pip install anthropic")
        return False
    try:
        client = anthropic.Anthropic(api_key=api_key)
        msg = client.messages.create(
            model="claude-3-5-haiku-latest",
            max_tokens=120,
            messages=[
                {
                    "role": "user",
                    "content": "用一句话总结：某公司营收同比+15%，净利同比+8%，PE 22。仅供参考，不构成投资建议。",
                }
            ],
        )
        text = "".join(block.text for block in msg.content if block.type == "text")
        print(f"  [成功] 模型返回：{text[:200]}")
        return True
    except Exception as e:  # noqa: BLE001
        print(f"  [失败] Anthropic 调用异常：{type(e).__name__}: {e}")
        return False


def main() -> int:
    print("TradeAI 连通性 spike —— 行情 + AI")
    results = {
        "akshare": check_akshare(),
        "yfinance": check_yfinance(),
        "anthropic": check_anthropic(),
    }
    _section("汇总")
    for name, ok in results.items():
        print(f"  {name:10s}: {'[OK] 通过' if ok else '[--] 跳过/失败'}")
    # 只要有任一行情源通过即视为 spike 成功
    market_ok = results["akshare"] or results["yfinance"]
    print(
        "\n行情连通性："
        + ("[OK] 至少一个数据源可用" if market_ok else "[--] 全部不可用（检查网络/依赖）")
    )
    return 0 if market_ok else 1


if __name__ == "__main__":
    sys.exit(main())
