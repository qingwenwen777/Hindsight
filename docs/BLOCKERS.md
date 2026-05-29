# 待处理事项 / 外部阻断汇总

> 由 Opus 在自动推进中遇到的、需要凭据或受网络限制的事项集中记录于此，便于你统一处理。

## 网络 / 数据源

- **[Step 1.3] AKShare 实时拉取在当前开发环境被拒连**
  - 现象：`ak.stock_zh_a_hist(...)` 抛 `Connection aborted / RemoteDisconnected`（重试 3 次仍失败）。
  - 影响：无法在本环境跑通"真实拉一只 A 股写库"的端到端验证。
  - 已做：同步逻辑（增量 + 校验 + UPSERT 幂等）用 mock 数据的单元测试全部通过；客户端对失败优雅降级（`AkShareUnavailable` → `SyncResult.ok=False`，不崩溃）。
  - 你需要做：在能访问东方财富数据接口的网络环境（国内网络通常可用）运行：
    ```powershell
    cd backend
    .\.venv\Scripts\Activate.ps1
    # 启动后端后调用：
    # POST /api/v1/stocks  登记 600519
    # POST /api/v1/admin/sync/prices?market=CN
    ```
  - 备注：yfinance（美股）在本环境可用，已验证。

## 凭据

- **[Phase 4] ANTHROPIC_API_KEY 未提供**
  - AI 模块（复盘 / 魔鬼代言人 / 失败模式）将实现"无 key 优雅降级"，但要真正调用需要你在 `backend/.env` 填入 `ANTHROPIC_API_KEY`。

## 依赖兼容

- **pandas-ta 与 numpy 2.x / pandas 3.x 不兼容**（Step 3.1 技术指标）— ✅ 已解决
  - `pandas-ta 0.3.x` 仍 `from numpy import NaN`（numpy 2.0 已移除）。
  - 处置：Step 3.1 已自实现 MA/EMA/MACD/RSI/布林带/KDJ（`services/analysis/indicators.py`），不依赖 pandas-ta，避免版本地狱。已从 pyproject 依赖移除 pandas-ta。


## 部署验证

- **[Step 6.3] `docker compose up -d` 未在本环境实跑**
  - 已提供 `backend/Dockerfile`、`frontend/Dockerfile`（Next standalone）、完整 `docker-compose.yml`（healthcheck/卷/环境变量齐全）。
  - 本环境无 Docker daemon，未实际构建镜像；后端 `pytest` 全绿、前端 `npm run build` 全绿，启动命令（alembic upgrade + uvicorn / node server.js）已在 Dockerfile 固化。
  - 你需要做：在装有 Docker 的机器上 `docker compose up -d` 验证；首次构建后端镜像会安装 akshare/scipy 等较重依赖，耗时数分钟属正常。
- 备份脚本 `python -m scripts.backup` 已本地实跑通过（生成 .gz 与 .gz.enc）。
