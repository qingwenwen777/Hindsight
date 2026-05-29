"""CSV 交易导入服务。

流程：上传 → 自动检测券商格式 → 字段映射 → 预览 → 批量写入。
导入的交易自动创建占位 journal（is_imported=true），允许后期补写。

支持的券商格式（列名签名）：
- generic: symbol,market,type,trade_date,quantity,price,currency[,commission,tax,other_fees]
- futu(富途): 代码,方向,成交数量,成交价格,成交金额,...（中文列）
- 其它券商可按 _BROKER_SIGNATURES 扩展。
"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, InvalidOperation

from sqlmodel import Session, select

from app.core.money import D
from app.models.base import utcnow
from app.models.journal import Journal
from app.models.stock import Stock
from app.models.transaction import Transaction


@dataclass
class ParsedRow:
    """解析后的一行（标准字段）。"""

    symbol: str
    market: str
    type: str
    trade_date: str
    quantity: str
    price: str
    currency: str
    commission: str = "0"
    tax: str = "0"
    other_fees: str = "0"
    error: str | None = None


@dataclass
class ImportPreview:
    """导入预览结果。"""

    broker: str
    columns: list[str]
    rows: list[ParsedRow] = field(default_factory=list)

    @property
    def valid_rows(self) -> list[ParsedRow]:
        return [r for r in self.rows if r.error is None]

    @property
    def invalid_rows(self) -> list[ParsedRow]:
        return [r for r in self.rows if r.error is not None]


# 券商签名：检测列名集合命中即判定格式
_BROKER_SIGNATURES: dict[str, set[str]] = {
    "futu": {"代码", "方向", "成交数量", "成交价格"},
    "xueqiu": {"股票代码", "操作", "数量", "价格"},
    "generic": {"symbol", "type", "trade_date", "quantity", "price"},
}

# 各券商列名 → 标准字段 的映射
_BROKER_MAPS: dict[str, dict[str, str]] = {
    "futu": {
        "代码": "symbol",
        "方向": "type",
        "成交数量": "quantity",
        "成交价格": "price",
        "成交时间": "trade_date",
        "货币": "currency",
        "佣金": "commission",
        "印花税": "tax",
    },
    "xueqiu": {
        "股票代码": "symbol",
        "操作": "type",
        "数量": "quantity",
        "价格": "price",
        "日期": "trade_date",
    },
}

# 方向词归一化
_SIDE_MAP = {
    "买入": "BUY", "买": "BUY", "buy": "BUY", "BUY": "BUY", "B": "BUY",
    "卖出": "SELL", "卖": "SELL", "sell": "SELL", "SELL": "SELL", "S": "SELL",
}


def detect_broker(columns: list[str]) -> str:
    """根据列名检测券商格式，返回 broker 名（默认 generic）。"""
    col_set = set(columns)
    best = "generic"
    best_score = 0
    for broker, sig in _BROKER_SIGNATURES.items():
        score = len(sig & col_set)
        if score > best_score and score >= max(2, len(sig) // 2):
            best = broker
            best_score = score
    return best


def _normalize_date(raw: str) -> str:
    """把多种日期格式归一为 ISO（取前 10 位）。"""
    raw = (raw or "").strip()
    # 常见 'YYYY-MM-DD HH:MM:SS' / 'YYYY/MM/DD'
    raw = raw.replace("/", "-")
    return raw[:10]


def _guess_market(symbol: str) -> str:
    """从代码猜市场（generic 无 market 列时兜底）。"""
    s = symbol.upper()
    if s.endswith(".HK"):
        return "HK"
    if s.endswith(".T"):
        return "JP"
    if s.isdigit() and len(s) == 6:
        return "CN"
    return "US"


def parse_csv(content: str, broker: str | None = None) -> ImportPreview:
    """解析 CSV 内容为预览（不写库）。"""
    reader = csv.DictReader(io.StringIO(content))
    columns = reader.fieldnames or []
    detected = broker or detect_broker(columns)
    preview = ImportPreview(broker=detected, columns=list(columns))

    col_map = _BROKER_MAPS.get(detected, {})

    for raw in reader:
        # 应用列映射（generic 直接用标准列名）
        std: dict[str, str] = {}
        if col_map:
            for src, dst in col_map.items():
                if src in raw and raw[src] not in (None, ""):
                    std[dst] = str(raw[src]).strip()
        else:
            std = {k: str(v).strip() for k, v in raw.items() if v is not None}

        symbol = std.get("symbol", "")
        market = std.get("market") or (_guess_market(symbol) if symbol else "")
        side = _SIDE_MAP.get(std.get("type", "").strip(), std.get("type", "").upper())
        row = ParsedRow(
            symbol=symbol,
            market=market,
            type=side,
            trade_date=_normalize_date(std.get("trade_date", "")),
            quantity=std.get("quantity", ""),
            price=std.get("price", ""),
            currency=std.get("currency", "") or _default_currency(market),
            commission=std.get("commission", "0") or "0",
            tax=std.get("tax", "0") or "0",
            other_fees=std.get("other_fees", "0") or "0",
        )
        row.error = _validate_row(row)
        preview.rows.append(row)

    return preview


def _default_currency(market: str) -> str:
    return {"CN": "CNY", "US": "USD", "HK": "HKD", "JP": "JPY"}.get(market, "USD")


def _validate_row(row: ParsedRow) -> str | None:
    """校验一行，返回错误信息或 None。"""
    if not row.symbol:
        return "缺少代码"
    if row.type not in ("BUY", "SELL"):
        return f"方向非法：{row.type}"
    try:
        date.fromisoformat(row.trade_date)
    except (ValueError, TypeError):
        return f"日期非法：{row.trade_date}"
    try:
        if D(row.quantity) <= 0 or D(row.price) <= 0:
            return "数量/价格必须 > 0"
    except (InvalidOperation, TypeError):
        return "数量/价格非数字"
    return None


def commit_import(session: Session, preview: ImportPreview) -> dict:
    """把预览中有效行批量写入，每行创建占位 journal(is_imported=true)。"""
    inserted = 0
    skipped = len(preview.invalid_rows)
    for row in preview.valid_rows:
        # 找/建股票
        stock = session.exec(
            select(Stock).where(Stock.symbol == row.symbol, Stock.market == row.market)
        ).first()
        if not stock:
            stock = Stock(
                symbol=row.symbol,
                market=row.market,
                name=row.symbol,  # 名称待同步补全
                currency=row.currency,
            )
            session.add(stock)
            session.flush()

        # 占位 journal（未锁定，允许后期补写）
        journal = Journal(
            stock_id=stock.id,
            decision_type=row.type,
            thesis="(导入交易，待补写决策日志)",
            is_imported=True,
            is_locked=False,
        )
        session.add(journal)
        session.flush()

        tx = Transaction(
            stock_id=stock.id,
            type=row.type,
            trade_date=date.fromisoformat(row.trade_date),
            quantity=D(row.quantity),
            price=D(row.price),
            currency=row.currency,
            commission=D(row.commission),
            tax=D(row.tax),
            other_fees=D(row.other_fees),
            journal_id=journal.id,
            is_imported=True,
        )
        session.add(tx)
        inserted += 1

    session.commit()
    # 失效缓存
    from app.services.analysis import pnl as pnl_service

    pnl_service.invalidate_holdings_cache()
    return {"inserted": inserted, "skipped": skipped, "broker": preview.broker}
