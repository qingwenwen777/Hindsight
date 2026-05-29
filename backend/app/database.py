"""数据库引擎与会话 —— SQLModel + SQLite(WAL)。"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlmodel import Session, SQLModel, create_engine

from app.config import settings

# SQLite 需要 check_same_thread=False 以配合 FastAPI 的多线程
_connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}

# 确保 SQLite 文件所在目录存在
if settings.database_url.startswith("sqlite"):
    _raw = settings.database_url.split("sqlite:///", 1)[-1]
    _db_path = Path(_raw)
    if not _db_path.is_absolute():
        from app.config import REPO_ROOT

        _db_path = REPO_ROOT / _raw
    _db_path.parent.mkdir(parents=True, exist_ok=True)

engine = create_engine(
    settings.database_url,
    echo=settings.debug,
    connect_args=_connect_args,
)


@event.listens_for(Engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record) -> None:  # noqa: ANN001
    """为每个 SQLite 连接启用 WAL 模式与外键约束。

    WAL 允许并发读写，foreign_keys 强制外键完整性。
    """
    # 仅对 SQLite 生效
    if not settings.database_url.startswith("sqlite"):
        return
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL;")
    cursor.execute("PRAGMA foreign_keys=ON;")
    cursor.execute("PRAGMA synchronous=NORMAL;")
    cursor.execute("PRAGMA busy_timeout=5000;")
    cursor.close()


def init_db() -> None:
    """创建所有表（开发/测试用；生产用 Alembic 迁移）。"""
    # 导入模型以注册到 SQLModel.metadata
    import app.models  # noqa: F401

    SQLModel.metadata.create_all(engine)


def get_session() -> Iterator[Session]:
    """FastAPI 依赖：提供数据库会话。"""
    with Session(engine) as session:
        yield session
