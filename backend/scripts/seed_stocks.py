"""预置常用股票脚本 —— 登记一批热门股票并同步历史行情。

按市场维护一份精选清单（symbol + 中文名 + 币种），登记入库后逐只同步日线。
名称优先用清单里写好的，缺字段时回退到 yfinance 发现结果。

用法：
    python -m scripts.seed_stocks                  # 全部市场
    python -m scripts.seed_stocks --market US      # 仅美股
    python -m scripts.seed_stocks --no-sync        # 只登记不拉行情
    python -m scripts.seed_stocks --list           # 只打印清单不执行
"""

from __future__ import annotations

import argparse
import sys

from sqlmodel import Session, select

from app.database import engine
from app.models.stock import Price, Stock
from app.services.data_sync.discovery import MARKET_CURRENCY
from app.services.data_sync.sync_service import sync_stock_prices

# 精选清单：market -> [(symbol, 中文名, 英文名, is_etf)]
# symbol 用内部格式：US 直接代码、HK 4位、JP 4位、CN 6位
SEED: dict[str, list[tuple[str, str, str, bool]]] = {
    "US": [
        ("AAPL", "苹果", "Apple Inc.", False),
        ("MSFT", "微软", "Microsoft Corporation", False),
        ("NVDA", "英伟达", "NVIDIA Corporation", False),
        ("GOOGL", "谷歌", "Alphabet Inc.", False),
        ("AMZN", "亚马逊", "Amazon.com Inc.", False),
        ("META", "Meta", "Meta Platforms Inc.", False),
        ("TSLA", "特斯拉", "Tesla Inc.", False),
        ("AVGO", "博通", "Broadcom Inc.", False),
        ("JPM", "摩根大通", "JPMorgan Chase & Co.", False),
        ("V", "维萨", "Visa Inc.", False),
        ("WMT", "沃尔玛", "Walmart Inc.", False),
        ("COST", "好市多", "Costco Wholesale Corp.", False),
        ("NFLX", "奈飞", "Netflix Inc.", False),
        ("AMD", "AMD", "Advanced Micro Devices Inc.", False),
        ("KO", "可口可乐", "The Coca-Cola Company", False),
        ("SPY", "标普500 ETF", "SPDR S&P 500 ETF Trust", True),
        ("QQQ", "纳指100 ETF", "Invesco QQQ Trust", True),
    ],
    "HK": [
        ("0700", "腾讯控股", "Tencent Holdings", False),
        ("9988", "阿里巴巴", "Alibaba Group", False),
        ("3690", "美团", "Meituan", False),
        ("9618", "京东集团", "JD.com", False),
        ("1810", "小米集团", "Xiaomi Corporation", False),
        ("0939", "建设银行", "China Construction Bank", False),
        ("0941", "中国移动", "China Mobile", False),
        ("1299", "友邦保险", "AIA Group", False),
        ("0388", "香港交易所", "HKEX", False),
        ("2318", "中国平安", "Ping An Insurance", False),
    ],
    "JP": [
        ("7203", "丰田汽车", "Toyota Motor Corp.", False),
        ("6758", "索尼集团", "Sony Group Corp.", False),
        ("9984", "软银集团", "SoftBank Group Corp.", False),
        ("6861", "基恩士", "Keyence Corp.", False),
        ("8306", "三菱日联金融", "Mitsubishi UFJ Financial", False),
        ("9983", "迅销(优衣库)", "Fast Retailing Co.", False),
        ("6098", "瑞可利", "Recruit Holdings", False),
        ("8035", "东京电子", "Tokyo Electron", False),
    ],
    "CN": [
        ("600519", "贵州茅台", "Kweichow Moutai", False),
        ("300750", "宁德时代", "CATL", False),
        ("601318", "中国平安", "Ping An Insurance", False),
        ("600036", "招商银行", "China Merchants Bank", False),
        ("000858", "五粮液", "Wuliangye", False),
        ("002594", "比亚迪", "BYD Company", False),
        ("600900", "长江电力", "China Yangtze Power", False),
        ("000333", "美的集团", "Midea Group", False),
        ("601899", "紫金矿业", "Zijin Mining", False),
        ("600276", "恒瑞医药", "Hengrui Pharma", False),
    ],
}


def _register(session: Session, market: str, symbol: str, name: str, name_en: str, is_etf: bool) -> Stock:
    """登记（已存在则返回现有）。"""
    existing = session.exec(
        select(Stock).where(Stock.symbol == symbol, Stock.market == market)
    ).first()
    if existing:
        return existing
    stock = Stock(
        symbol=symbol,
        market=market,
        name=name,
        name_en=name_en,
        currency=MARKET_CURRENCY[market],
        is_etf=is_etf,
    )
    session.add(stock)
    session.commit()
    session.refresh(stock)
    return stock


def _has_prices(session: Session, stock_id: int) -> bool:
    return (
        session.exec(select(Price.date).where(Price.stock_id == stock_id).limit(1)).first()
        is not None
    )


def seed(markets: list[str], do_sync: bool = True, force: bool = False) -> None:
    """执行预置。"""
    total_reg = 0
    total_sync_ok = 0
    total_sync_fail = 0
    with Session(engine) as session:
        for market in markets:
            items = SEED.get(market, [])
            if not items:
                continue
            print(f"\n=== {market} （{len(items)} 只）===")
            for symbol, name, name_en, is_etf in items:
                stock = _register(session, market, symbol, name, name_en, is_etf)
                total_reg += 1
                tag = f"{market} {symbol} {name}"
                if not do_sync:
                    print(f"  登记 {tag}")
                    continue
                if not force and _has_prices(session, stock.id):  # type: ignore[arg-type]
                    print(f"  跳过同步 {tag}（已有行情）")
                    continue
                result = sync_stock_prices(session, stock, full=True)
                if result.ok:
                    total_sync_ok += 1
                    print(f"  同步 {tag}: {result.message} [{result.source}]")
                else:
                    total_sync_fail += 1
                    print(f"  同步失败 {tag}: {result.message}")

    print(
        f"\n完成：登记 {total_reg} 只"
        + (f"，同步成功 {total_sync_ok}，失败 {total_sync_fail}" if do_sync else "（未同步）")
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="预置常用股票")
    parser.add_argument(
        "--market",
        choices=["US", "HK", "JP", "CN"],
        help="只处理指定市场（默认全部）",
    )
    parser.add_argument("--no-sync", action="store_true", help="只登记不同步行情")
    parser.add_argument("--force", action="store_true", help="已有行情也重新全量同步")
    parser.add_argument("--list", action="store_true", help="只打印清单，不执行")
    args = parser.parse_args()

    target_markets = [args.market] if args.market else ["US", "HK", "JP", "CN"]

    if args.list:
        for m in target_markets:
            print(f"\n=== {m} ===")
            for symbol, name, name_en, is_etf in SEED.get(m, []):
                print(f"  {symbol:8} {name}  ({name_en}){' [ETF]' if is_etf else ''}")
        sys.exit(0)

    seed(target_markets, do_sync=not args.no_sync, force=args.force)
