# 后端镜像 —— FastAPI + SQLite
FROM python:3.11-slim

# 系统依赖（akshare/lxml 等可能需要）
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ sqlite3 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 先装依赖（利用缓存）
COPY pyproject.toml ./
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir .

# 拷贝应用代码
COPY app ./app
COPY alembic ./alembic
COPY alembic.ini ./

# 数据目录（compose 会挂载宿主机卷）
RUN mkdir -p /app/data

EXPOSE 8000

# 启动：先迁移再起服务
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
