"""CSV 导入测试：检测、预览、批量写入闭环。"""

from __future__ import annotations

import io

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.models.journal import Journal
from app.models.transaction import Transaction
from app.services.import_csv import detect_broker, parse_csv


def test_detect_generic() -> None:
    cols = ["symbol", "market", "type", "trade_date", "quantity", "price", "currency"]
    assert detect_broker(cols) == "generic"


def test_detect_futu() -> None:
    cols = ["代码", "方向", "成交数量", "成交价格", "成交时间"]
    assert detect_broker(cols) == "futu"


def test_parse_generic_validation() -> None:
    csv_text = (
        "symbol,market,type,trade_date,quantity,price,currency\n"
        "600519,CN,BUY,2026-01-02,100,1700,CNY\n"
        "AAPL,US,SELL,2026-01-03,10,200,USD\n"
        "BAD,US,FOO,2026-01-03,10,200,USD\n"  # 方向非法
    )
    preview = parse_csv(csv_text)
    assert preview.broker == "generic"
    assert len(preview.valid_rows) == 2
    assert len(preview.invalid_rows) == 1
    assert "方向非法" in preview.invalid_rows[0].error


def test_import_commit_closed_loop(client: TestClient, session: Session) -> None:
    """上传 generic CSV → 写入交易 + 占位 journal(is_imported=true)。"""
    csv_text = (
        "symbol,market,type,trade_date,quantity,price,currency\n"
        "600519,CN,BUY,2026-01-02,100,1700,CNY\n"
    )
    files = {"file": ("trades.csv", io.BytesIO(csv_text.encode("utf-8")), "text/csv")}
    resp = client.post("/api/v1/transactions/import", files=files)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["inserted"] == 1
    assert data["broker"] == "generic"

    # 交易已写入
    tx = session.exec(select(Transaction)).one()
    assert tx.is_imported is True
    assert tx.quantity == __import__("decimal").Decimal("100")
    # 占位 journal 未锁定（允许补写）
    j = session.get(Journal, tx.journal_id)
    assert j.is_imported is True
    assert j.is_locked is False


def test_import_preview_endpoint(client: TestClient) -> None:
    """预览端点返回有效/无效行统计，不写库。"""
    csv_text = (
        "代码,方向,成交数量,成交价格,成交时间,货币\n"
        "0700.HK,买入,500,300,2026-02-01 10:00:00,HKD\n"
    )
    files = {"file": ("futu.csv", io.BytesIO(csv_text.encode("utf-8-sig")), "text/csv")}
    resp = client.post("/api/v1/transactions/import/preview", files=files)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["broker"] == "futu"
    assert data["valid"] == 1
    assert data["rows"][0]["symbol"] == "0700.HK"
    assert data["rows"][0]["type"] == "BUY"
    assert data["rows"][0]["market"] == "HK"
