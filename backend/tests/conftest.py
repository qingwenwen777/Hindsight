"""pytest 公共夹具：内存 SQLite 会话 + FastAPI 依赖覆盖。"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app.database import get_session
from app.main import app


@pytest.fixture(name="engine")
def engine_fixture():
    """每个测试一个独立的内存库（StaticPool 保证同一连接）。"""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    yield engine
    SQLModel.metadata.drop_all(engine)


@pytest.fixture(name="session")
def session_fixture(engine) -> Iterator[Session]:  # noqa: ANN001
    with Session(engine) as session:
        yield session


@pytest.fixture(name="client")
def client_fixture(session: Session) -> Iterator[TestClient]:
    """注入测试会话的 TestClient。"""

    def _get_session_override() -> Iterator[Session]:
        yield session

    app.dependency_overrides[get_session] = _get_session_override
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def _clear_holdings_cache() -> Iterator[None]:
    """每个测试前后清空进程内持仓缓存，避免跨测试串味。"""
    from app.services.analysis import pnl as pnl_service

    pnl_service.invalidate_holdings_cache()
    yield
    pnl_service.invalidate_holdings_cache()
