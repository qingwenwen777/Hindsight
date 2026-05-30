"""应用配置 —— 用 pydantic-settings 管理，敏感值走 .env。"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# 项目根（backend/）目录
BACKEND_DIR = Path(__file__).resolve().parent.parent
# 仓库根目录（TradeAI/）
REPO_ROOT = BACKEND_DIR.parent
# 默认数据目录
DEFAULT_DATA_DIR = REPO_ROOT / "data"


class Settings(BaseSettings):
    """全局配置。

    所有字段都可由环境变量或 .env 覆盖（不区分大小写）。
    """

    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ---- 基础 ----
    app_name: str = "TradeAI Backend"
    debug: bool = False
    api_prefix: str = "/api/v1"

    # ---- 数据库 ----
    # SQLite 路径；Docker 内会被 DATABASE_URL 覆盖
    database_url: str = f"sqlite:///{(DEFAULT_DATA_DIR / 'stock.db').as_posix()}"

    # ---- 货币 ----
    base_currency: str = "JPY"

    # ---- AI ----
    anthropic_api_key: str | None = None
    ai_monthly_budget_jpy: int = 2000
    # AI 服务端点与模型（可指向 Anthropic 官方或兼容端点如 DeepSeek 的 /anthropic）
    ai_base_url: str | None = None
    # 覆盖所有任务的模型名（如 DeepSeek 的 deepseek-chat）；为空则用内置分级表
    ai_model: str | None = None

    # ---- 时区 ----
    display_timezone: str = "Asia/Tokyo"

    # ---- 调度 ----
    enable_scheduler: bool = False

    # ---- CORS ----
    # 默认开发地址；生产用 CORS_ORIGINS 环境变量追加（逗号分隔），或设为 "*" 放开
    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]
    extra_cors_origins: str = ""  # 逗号分隔，或 "*"

    @property
    def allowed_origins(self) -> list[str]:
        """合并默认与环境追加的 CORS 来源。"""
        if self.extra_cors_origins.strip() == "*":
            return ["*"]
        extra = [o.strip() for o in self.extra_cors_origins.split(",") if o.strip()]
        return [*self.cors_origins, *extra]

    @property
    def data_dir(self) -> Path:
        """从 database_url 推导数据目录，确保备份/导出落在同一处。"""
        if self.database_url.startswith("sqlite"):
            # sqlite:///abs/path 或 sqlite:////abs/path
            raw = self.database_url.split("sqlite:///", 1)[-1]
            db_path = Path(raw)
            if not db_path.is_absolute():
                db_path = REPO_ROOT / raw
            return db_path.parent
        return DEFAULT_DATA_DIR


@lru_cache
def get_settings() -> Settings:
    """单例配置，避免重复读取 .env。"""
    return Settings()


settings = get_settings()
