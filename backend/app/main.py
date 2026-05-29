"""FastAPI 应用入口。"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import settings
from app.core.journal_lock import JournalLockedError, install_journal_lock_guard
from app.core.response import ok
from app.logging_config import configure_logging, get_logger

configure_logging(debug=settings.debug)
log = get_logger(__name__)

# 注册日志锁定守卫（拦截对已锁定 journal 的 UPDATE）
install_journal_lock_guard()


@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: ANN201
    """应用生命周期：启动时记录日志（建表交给 Alembic）。"""
    log.info("app.startup", app_name=settings.app_name, base_currency=settings.base_currency)
    if settings.enable_scheduler:
        from app.services.data_sync.scheduler import shutdown_scheduler, start_scheduler

        start_scheduler()
        try:
            yield
        finally:
            shutdown_scheduler()
    else:
        yield
    log.info("app.shutdown")


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="个人股票分析、记录与复盘平台 API",
    lifespan=lifespan,
)

# CORS（前端开发地址）
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):  # noqa: ANN201
    """把 HTTP 异常包装成统一响应壳。"""
    return JSONResponse(
        status_code=exc.status_code,
        content={"code": exc.status_code, "message": str(exc.detail), "data": None, "meta": None},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):  # noqa: ANN201
    """把请求校验错误（422）包装成统一响应壳。"""
    return JSONResponse(
        status_code=422,
        content={
            "code": 422,
            "message": "请求参数校验失败",
            "data": {"errors": exc.errors()},
            "meta": None,
        },
    )


@app.exception_handler(JournalLockedError)
async def journal_locked_handler(request: Request, exc: JournalLockedError):  # noqa: ANN201
    """已锁定日志被修改 → 403。"""
    return JSONResponse(
        status_code=403,
        content={"code": 403, "message": str(exc), "data": None, "meta": None},
    )


@app.get("/health", tags=["system"])
async def health() -> dict:
    """健康检查接口，返回统一响应壳。"""
    return ok({"status": "healthy", "app": settings.app_name})


# ---- 路由注册（随各 Phase 增加）----
from app.api import admin, cash, journals, portfolio, returns, stocks, transactions  # noqa: E402

app.include_router(stocks.router, prefix=settings.api_prefix)
app.include_router(transactions.router, prefix=settings.api_prefix)
app.include_router(journals.router, prefix=settings.api_prefix)
app.include_router(portfolio.router, prefix=settings.api_prefix)
app.include_router(cash.router, prefix=settings.api_prefix)
app.include_router(returns.router, prefix=settings.api_prefix)
app.include_router(admin.router, prefix=settings.api_prefix)
