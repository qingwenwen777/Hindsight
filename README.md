# 个人股票分析平台 (TradeAI)

> 一个面向个人投资者的股票分析、记录与复盘平台。
> 核心目标：**学习投资 + 对抗认知偏差**，深度集成 AI 作为"投资教练"。

唯一事实来源：[`docs/stock-analyzer-design-v1.1.md`](docs/stock-analyzer-design-v1.1.md)

---

## 技术栈

- **后端**：Python 3.11+ · FastAPI · SQLModel · SQLite(WAL) · Alembic · pandas · APScheduler · anthropic SDK
- **前端**：Next.js 14 (App Router) · TypeScript · Tailwind · shadcn/ui · TanStack Query · Zustand · lightweight-charts
- **金额**：全链路 `Decimal`（DB 用 TEXT 存储），杜绝浮点误差

---

## 目录结构

```
TradeAI/
├── backend/      # FastAPI 后端
├── frontend/     # Next.js 前端
├── data/         # SQLite 库 + 备份 + 导出
└── docs/         # 设计文档
```

---

## 本地启动

### 方式一：Docker Compose（推荐）

```bash
docker compose up -d
```

- 前端：http://localhost:3000
- 后端：http://localhost:8000 （文档 http://localhost:8000/docs）

### 方式二：本地开发

**后端**（Windows / PowerShell）

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
copy .env.example .env   # 填入 ANTHROPIC_API_KEY（可选）
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

**前端**

```powershell
cd frontend
npm install
npm run dev
```

---

## 远程访问

- **首选 Tailscale**：零配置 VPN，数据不出公网，手机可用。
- **次选 Cloudflare Tunnel**：免费 + 自定义域名 + 加密。
- 即便单用户本地部署，Web 入口也应有密码登录，不要裸奔。

---

## 环境注意事项

- 行情数据源：AKShare（A 股/港股）、yfinance（美股/日股）。AKShare 首次使用可能需要额外依赖，详见同步模块说明。
- AI 功能需要 `ANTHROPIC_API_KEY`，缺失时相关功能优雅降级。

---

## 开发进度

按 `docs/build-prompt-for-opus.md` 路线图分 Phase 推进，详见各阶段提交记录。
