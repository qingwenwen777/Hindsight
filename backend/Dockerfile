# 后端镜像 —— FastAPI + SQLite
FROM python:3.11-slim

# 系统依赖（akshare/lxml/scipy 等可能需要编译工具）
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ sqlite3 curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

ENV PIP_NO_CACHE_DIR=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# 拷贝项目元信息与源码后再安装（setuptools 需要包存在才能发现 app*）
COPY pyproject.toml ./
COPY app ./app
COPY alembic ./alembic
COPY alembic.ini ./

RUN pip install --upgrade pip && \
    pip install .

# 数据目录（compose 会挂载宿主机卷）
RUN mkdir -p /app/data

EXPOSE 8000

# 启动：先迁移再起服务
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
