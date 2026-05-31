"""桌面版后端入口（PyInstaller 冻结后运行）。

与 docker 的 `alembic upgrade head && uvicorn ...` 等价，但全部在进程内完成，
不依赖外部 alembic CLI 或 shell。要点：

1. 数据库放到用户数据目录（%APPDATA%/TradeAI），避免覆盖安装丢数据。
2. 冻结环境下 alembic 脚本路径指向 PyInstaller 解包目录（sys._MEIPASS）。
3. 端口从命令行参数或环境变量读取（外壳会分配空闲端口）。
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


def _is_frozen() -> bool:
    """是否运行在 PyInstaller 冻结环境。"""
    return getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS")


def _bundle_dir() -> Path:
    """资源根目录：冻结时为 _MEIPASS 解包目录，否则为本文件所在目录。"""
    if _is_frozen():
        return Path(sys._MEIPASS)  # type: ignore[attr-defined]
    return Path(__file__).resolve().parent


def _user_data_dir() -> Path:
    """用户数据目录（Windows: %APPDATA%/TradeAI）。"""
    base = os.environ.get("APPDATA") or os.path.expanduser("~")
    d = Path(base) / "TradeAI"
    (d / "data").mkdir(parents=True, exist_ok=True)
    return d


def _configure_environment() -> tuple[str, int]:
    """在导入 app 之前设置好环境变量，返回 (host, port)。"""
    data_dir = _user_data_dir()
    db_path = (data_dir / "data" / "stock.db").as_posix()

    # SQLAlchemy SQLite 绝对路径：
    # - Windows 盘符路径（C:/...）用三斜杠：sqlite:///C:/...
    # - POSIX 绝对路径（/...）用四斜杠：sqlite:////...
    if len(db_path) >= 2 and db_path[1] == ":":
        db_url = f"sqlite:///{db_path}"
    else:
        db_url = f"sqlite:////{db_path.lstrip('/')}"

    # 让 app.config 读取到桌面版的数据库路径
    os.environ.setdefault("DATABASE_URL", db_url)
    # 桌面版默认开启调度（每日自动更新行情）
    os.environ.setdefault("ENABLE_SCHEDULER", "true")
    # 仅本机访问
    os.environ.setdefault("EXTRA_CORS_ORIGINS", "*")

    host = os.environ.get("TRADEAI_HOST", "127.0.0.1")
    port = int(os.environ.get("TRADEAI_PORT", sys.argv[1] if len(sys.argv) > 1 else "8000"))
    return host, port


def _run_migrations() -> None:
    """在进程内执行 alembic 迁移到 head（等价 `alembic upgrade head`）。"""
    from alembic import command
    from alembic.config import Config

    bundle = _bundle_dir()
    ini_path = bundle / "alembic.ini"
    script_path = bundle / "alembic"

    cfg = Config(str(ini_path))
    cfg.set_main_option("script_location", str(script_path))
    # env.py 会用 app.config 的 DATABASE_URL 覆盖，这里仅兜底
    cfg.set_main_option("sqlalchemy.url", os.environ["DATABASE_URL"])
    command.upgrade(cfg, "head")


def main() -> None:
    host, port = _configure_environment()
    _run_migrations()

    import uvicorn

    from app.main import app

    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()
