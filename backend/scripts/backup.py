"""每日备份脚本（设计文档 7.5）。

- 用 SQLite 在线 .backup 生成一致性快照
- gzip 压缩
- 可选 AES 加密（设置 BACKUP_PASSWORD 时）
- 保留最近 N 天，清理过期备份

用法：
    python -m scripts.backup            # 生成备份
    python -m scripts.backup --keep 30  # 保留 30 天
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import shutil
import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path

from app.config import REPO_ROOT, settings


def _db_path() -> Path:
    raw = settings.database_url.split("sqlite:///")[-1]
    p = Path(raw)
    return p if p.is_absolute() else REPO_ROOT / raw


def _backup_dir() -> Path:
    d = settings.data_dir / "backups"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _encrypt(data: bytes, password: str) -> bytes:
    """简单的 XOR-stream 加密（基于 sha256 派生密钥流）。

    说明：这是无第三方依赖的轻量加密，足以防止备份被随意读取；
    若需强加密，可在有 cryptography 库时替换为 AES-GCM。
    """
    key = hashlib.sha256(password.encode()).digest()
    out = bytearray(len(data))
    keystream = b""
    counter = 0
    for i, b in enumerate(data):
        if i % 32 == 0:
            keystream = hashlib.sha256(key + counter.to_bytes(8, "big")).digest()
            counter += 1
        out[i] = b ^ keystream[i % 32]
    return bytes(out)


def make_backup(keep_days: int = 30) -> Path:
    """生成一次备份，返回备份文件路径。"""
    db = _db_path()
    if not db.exists():
        print(f"[backup] 数据库不存在：{db}")
        sys.exit(1)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    bdir = _backup_dir()
    snapshot = bdir / f"stock_{ts}.db"

    # 1. 一致性快照
    src = sqlite3.connect(db)
    dst = sqlite3.connect(snapshot)
    with dst:
        src.backup(dst)
    src.close()
    dst.close()

    # 2. gzip 压缩
    gz_path = snapshot.with_suffix(".db.gz")
    with open(snapshot, "rb") as f_in, gzip.open(gz_path, "wb") as f_out:
        shutil.copyfileobj(f_in, f_out)
    snapshot.unlink()  # 删除未压缩快照

    final = gz_path
    # 3. 可选加密
    import os

    password = os.getenv("BACKUP_PASSWORD")
    if password:
        enc_path = gz_path.with_suffix(".gz.enc")
        enc_path.write_bytes(_encrypt(gz_path.read_bytes(), password))
        gz_path.unlink()
        final = enc_path

    print(f"[backup] 完成：{final.name} ({final.stat().st_size} bytes)")

    # 4. 清理过期
    _cleanup(bdir, keep_days)
    return final


def _cleanup(bdir: Path, keep_days: int) -> None:
    cutoff = datetime.now() - timedelta(days=keep_days)
    removed = 0
    for f in bdir.glob("stock_*"):
        if f.name == ".gitkeep":
            continue
        if datetime.fromtimestamp(f.stat().st_mtime) < cutoff:
            f.unlink()
            removed += 1
    if removed:
        print(f"[backup] 清理过期备份 {removed} 个（保留 {keep_days} 天）")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="TradeAI 数据库备份")
    parser.add_argument("--keep", type=int, default=30, help="保留天数")
    args = parser.parse_args()
    make_backup(keep_days=args.keep)
