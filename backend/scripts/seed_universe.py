"""扩充股票池 —— 批量登记各市场精选成分股并同步行情/财务。

复用既有登记 + sync_stock_prices + fetch_financials 流程，分批、失败跳过、幂等。

用法：
    python -m scripts.seed_universe                 # 全部市场
    python -m scripts.seed_universe --market US     # 仅美股
    python -m scripts.seed_universe --no-sync       # 只登记不拉数据
    python -m scripts.seed_universe --list          # 只打印清单
"""

from __future__ import annotations

import argparse
import sys

from sqlmodel import Session, select

from app.database import engine
from app.logging_config import get_logger
from app.models.financials import Financial
from app.models.stock import Stock
from app.services.data_sync.discovery import MARKET_CURRENCY

log = get_logger(__name__)

# 精选成分股：market -> [(symbol, 中文名, 英文名)]
# 控制规模（每市场数十只），避免一次几千只压垮 SQLite/数据源。
UNIVERSE: dict[str, list[tuple[str, str, str]]] = {
    "US": [
        ("AAPL", "苹果", "Apple"), ("MSFT", "微软", "Microsoft"),
        ("NVDA", "英伟达", "NVIDIA"), ("GOOGL", "谷歌A", "Alphabet A"),
        ("AMZN", "亚马逊", "Amazon"), ("META", "Meta", "Meta Platforms"),
        ("TSLA", "特斯拉", "Tesla"), ("AVGO", "博通", "Broadcom"),
        ("JPM", "摩根大通", "JPMorgan"), ("V", "维萨", "Visa"),
        ("MA", "万事达", "Mastercard"), ("WMT", "沃尔玛", "Walmart"),
        ("COST", "好市多", "Costco"), ("NFLX", "奈飞", "Netflix"),
        ("AMD", "AMD", "AMD"), ("KO", "可口可乐", "Coca-Cola"),
        ("PEP", "百事", "PepsiCo"), ("ORCL", "甲骨文", "Oracle"),
        ("CRM", "Salesforce", "Salesforce"), ("ADBE", "Adobe", "Adobe"),
        ("MCD", "麦当劳", "McDonald's"), ("DIS", "迪士尼", "Disney"),
        ("INTC", "英特尔", "Intel"), ("QCOM", "高通", "Qualcomm"),
        ("PFE", "辉瑞", "Pfizer"), ("JNJ", "强生", "Johnson & Johnson"),
        ("UNH", "联合健康", "UnitedHealth"), ("HD", "家得宝", "Home Depot"),
        ("BAC", "美国银行", "Bank of America"), ("XOM", "埃克森美孚", "Exxon Mobil"),
    ],
    "HK": [
        ("0700", "腾讯控股", "Tencent"), ("9988", "阿里巴巴", "Alibaba"),
        ("3690", "美团", "Meituan"), ("9618", "京东集团", "JD.com"),
        ("1810", "小米集团", "Xiaomi"), ("0939", "建设银行", "CCB"),
        ("0941", "中国移动", "China Mobile"), ("1299", "友邦保险", "AIA"),
        ("0388", "香港交易所", "HKEX"), ("2318", "中国平安", "Ping An"),
        ("1398", "工商银行", "ICBC"), ("3988", "中国银行", "Bank of China"),
        ("0883", "中国海洋石油", "CNOOC"), ("0005", "汇丰控股", "HSBC"),
        ("2628", "中国人寿", "China Life"), ("1024", "快手", "Kuaishou"),
        ("9999", "网易", "NetEase"), ("2020", "安踏体育", "ANTA"),
    ],
    "JP": [
        ("7203", "丰田汽车", "Toyota"), ("6758", "索尼集团", "Sony"),
        ("9984", "软银集团", "SoftBank"), ("6861", "基恩士", "Keyence"),
        ("8306", "三菱日联金融", "Mitsubishi UFJ"), ("9983", "迅销", "Fast Retailing"),
        ("6098", "瑞可利", "Recruit"), ("8035", "东京电子", "Tokyo Electron"),
        ("4063", "信越化学", "Shin-Etsu"), ("9433", "KDDI", "KDDI"),
        ("8058", "三菱商事", "Mitsubishi Corp"), ("7974", "任天堂", "Nintendo"),
        ("6501", "日立", "Hitachi"), ("7267", "本田", "Honda"),
    ],
    "CN": [
        ("600519", "贵州茅台", "Kweichow Moutai"), ("300750", "宁德时代", "CATL"),
        ("601318", "中国平安", "Ping An"), ("600036", "招商银行", "CMB"),
        ("000858", "五粮液", "Wuliangye"), ("002594", "比亚迪", "BYD"),
        ("600900", "长江电力", "Yangtze Power"), ("000333", "美的集团", "Midea"),
        ("601899", "紫金矿业", "Zijin Mining"), ("600276", "恒瑞医药", "Hengrui"),
        ("601012", "隆基绿能", "LONGi"), ("000651", "格力电器", "Gree"),
        ("600030", "中信证券", "CITIC Securities"), ("601166", "兴业银行", "Industrial Bank"),
        ("000001", "平安银行", "Ping An Bank"), ("600887", "伊利股份", "Yili"),
        ("002415", "海康威视", "Hikvision"), ("300059", "东方财富", "East Money"),
    ],
}


def _register(session: Session, market: str, symbol: str, name: str, name_en: str) -> Stock:
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
    )
    session.add(stock)
    session.commit()
    session.refresh(stock)
    return stock


def _has_prices(session: Session, stock_id: int) -> bool:
    from app.models.stock import Price

    return session.exec(select(Price.date).where(Price.stock_id == stock_id).limit(1)).first() is not None


def seed_universe(markets: list[str], do_sync: bool = True) -> dict:
    """执行扩充。返回统计。"""
    from sqlalchemy.dialects.sqlite import insert as sqlite_insert

    from app.services.data_sync.financials_client import fetch_financials
    from app.services.data_sync.sync_service import sync_stock_prices

    stats = {"registered": 0, "synced": 0, "fin": 0, "failed": []}
    with Session(engine) as session:
        for market in markets:
            items = UNIVERSE.get(market, [])
            print(f"\n=== {market}（{len(items)} 只）===")
            for symbol, name, name_en in items:
                try:
                    stock = _register(session, market, symbol, name, name_en)
                    stats["registered"] += 1
                    if not do_sync:
                        print(f"  登记 {market} {symbol} {name}")
                        continue
                    if not _has_prices(session, stock.id):  # type: ignore[arg-type]
                        res = sync_stock_prices(session, stock, full=True)
                        if res.ok:
                            stats["synced"] += 1
                            print(f"  同步 {market} {symbol} {name}: {res.message} [{res.source}]")
                        else:
                            stats["failed"].append(f"{market}:{symbol}")
                            print(f"  同步失败 {market} {symbol}: {res.message}")
                    else:
                        print(f"  跳过同步 {market} {symbol}（已有行情）")
                    # 财务
                    try:
                        fin_data = fetch_financials(symbol, market)
                        if fin_data:
                            values = {"stock_id": stock.id, **fin_data}
                            ins = sqlite_insert(Financial).values(**values)
                            ins = ins.on_conflict_do_update(
                                index_elements=["stock_id", "as_of"],
                                set_={k: ins.excluded[k] for k in fin_data if k != "as_of"},
                            )
                            session.exec(ins)
                            session.commit()
                            stats["fin"] += 1
                    except Exception as e:  # noqa: BLE001
                        log.warning("seed_universe.fin_failed", symbol=symbol, error=str(e))
                except Exception as e:  # noqa: BLE001
                    stats["failed"].append(f"{market}:{symbol}")
                    log.warning("seed_universe.failed", market=market, symbol=symbol, error=str(e))
    print(
        f"\n完成：登记 {stats['registered']}，同步 {stats['synced']}，"
        f"财务 {stats['fin']}，失败 {len(stats['failed'])}"
    )
    return stats


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="扩充股票池（成分股）")
    parser.add_argument("--market", choices=["US", "HK", "JP", "CN"])
    parser.add_argument("--no-sync", action="store_true")
    parser.add_argument("--list", action="store_true")
    args = parser.parse_args()

    target = [args.market] if args.market else ["US", "HK", "JP", "CN"]
    if args.list:
        for m in target:
            print(f"\n=== {m} ===")
            for sym, name, name_en in UNIVERSE.get(m, []):
                print(f"  {sym:8} {name} ({name_en})")
        sys.exit(0)
    seed_universe(target, do_sync=not args.no_sync)
