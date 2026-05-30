# Design Document

> AI 洞察中心（日报 Agent + 规则筛选器）

## Overview

本设计在现有 Hindsight 平台上新增 **AI 洞察** 板块，落地需求文档的 11 条需求。核心策略是 **最大化复用既有基础设施**：APScheduler 调度、`BudgetGuard` 预算守卫、`ai_client.analyze`（缓存+降级）、`context_builder`（代码算数字、AI 只定性）、discovery+sync 流程、统一响应壳、i18n。

三条主线：

1. **AI 洞察文档**：统一的 Markdown 文档存储（`InsightDocument`），承载日报与筛选点评，前端在新导航板块以安全渲染的方式阅读、下载、按类型/市场分页，90 天自动清理。
2. **日报 Agent**：可配置（`ReportConfig`）的定时/手动生成器，组装"与我相关"的上下文（持仓/关注异动、触价、决策日志对照、待办、市场概览复用基准指数），调用 AI 产出 Markdown，失败优雅降级。
3. **规则筛选器 + AI 点评**：确定性筛选引擎（`ScreenerRule` + 执行器，**不调 AI**），结果可再请求 AI 定性点评（多空/风险/待调研，**禁买卖信号**）并存为文档。

配套：**股票池扩充**（批量导入成分股，复用 discovery+sync）与 **顶栏价格提醒**（触及目标价/止损价，聚合进现有铃铛）。

### 设计原则
- 数字由代码算，AI 只定性（延续既有 `context_builder` 模式）。
- 所有 AI 产出受 `BudgetGuard` 约束，超限/无 Key 走降级路径。
- 新表经 Alembic 迁移，不破坏既有数据。
- 前端文案全部走 i18n（中/日/英）；AI 正文语言由配置决定，独立于界面语言。
- 单用户：配置/规则全局单份，无鉴权。

---

## Architecture

```
                         ┌─────────────────────────────────────────┐
                         │            前端 (Next.js)                │
                         │  /insights  (列表/详情/下载)              │
                         │  /insights/config  (日报配置)            │
                         │  /insights/screener (规则筛选 + 点评)     │
                         │  Topbar 铃铛 (复盘提醒 + 价格提醒聚合)     │
                         └───────────────┬─────────────────────────┘
                                         │ /api/v1
                         ┌───────────────▼─────────────────────────┐
                         │              FastAPI 路由                 │
                         │  api/insights.py   api/screener.py        │
                         │  api/admin.py(+股票池导入)  api/alerts*    │
                         └───┬───────────┬───────────┬──────────────┘
                             │           │           │
              ┌──────────────▼┐  ┌───────▼────────┐  ┌▼───────────────┐
              │ daily_report   │  │ screener        │  │ price_alerts   │
              │ service        │  │ service(纯计算) │  │ service        │
              │ (组装+AI+降级) │  │  + AI 点评      │  │                │
              └───┬────────┬───┘  └───────┬────────┘  └───┬────────────┘
                  │        │              │               │
        ┌─────────▼┐  ┌────▼──────────────▼───┐   ┌───────▼─────────┐
        │ ai_client │  │ context (复用 builder) │   │ 既有 reminders   │
        │ +Budget   │  │ benchmark/pnl/financ. │   │ + 新 alerts 表   │
        └───────────┘  └───────────────────────┘   └─────────────────┘
                  │
        ┌─────────▼───────────────────────────────────────┐
        │  新模型: InsightDocument / ReportConfig /         │
        │  ScreenerRule / PriceAlert   (SQLite + Alembic)   │
        └───────────────────────────────────────────────────┘
                  │
        ┌─────────▼───────────┐
        │ APScheduler (既有)  │  新增 jobs:
        │  - 日报(每市场定时)  │  - 价格提醒(同步后评估)
        │  - 90天清理(每日)    │
        └─────────────────────┘
```

---

## Components and Interfaces

### 1. 数据模型（`backend/app/models/insight.py`）

```python
class InsightDocument(SQLModel, table=True):
    """AI 洞察文档（日报 / 筛选点评），Markdown 正文。"""
    __tablename__ = "insight_documents"
    id: int | None = primary_key
    doc_type: str          # DAILY_REPORT | SCREENER_REVIEW
    market: str | None     # US/CN/HK/JP（筛选点评可为空或多市场）
    title: str
    body_md: str           # Markdown 正文
    report_date: date | None  # 日报对应日期（用于按天去重）
    model: str | None
    prompt_tokens: int | None
    completion_tokens: int | None
    degraded: bool = False         # 是否降级生成
    degraded_reason: str | None
    source_ref: dict | None (JSON) # {config_id} 或 {rule_id, symbols:[...]}
    is_read: bool = False
    created_at: datetime (index)
    # 唯一性：同一天同一市场的日报唯一 → (doc_type, market, report_date)

class ReportConfig(SQLModel, table=True):
    """日报配置（单用户，全局单份；id 固定为 1）。"""
    __tablename__ = "report_configs"
    id: int | None = primary_key
    enabled_markets: list[str] (JSON)   # ["US","CN"...]
    schedule: dict (JSON)               # {"US":"06:30","CN":"16:30",...}
    move_threshold_pct: Decimal = 5     # 异动阈值
    detail_level: str = "STANDARD"      # BRIEF|STANDARD|DETAILED
    tone: str = "NEUTRAL"               # CONSERVATIVE|NEUTRAL
    language: str = "zh"                # zh|ja|en（AI 正文语言）
    focus_text: str | None              # 自由文本：重点关注主题/行业/关键词
    constraints: list[str] (JSON)       # 自定义约束清单
    updated_at: datetime

class ScreenerRule(SQLModel, table=True):
    """命名筛选规则。"""
    __tablename__ = "screener_rules"
    id: int | None = primary_key
    name: str
    conditions: list[dict] (JSON)  # [{field,op,value} | {field,op,value,value2}]
    markets: list[str] | None (JSON)
    created_at / updated_at

class PriceAlert(SQLModel, table=True):
    """价格提醒（触及目标价/止损价）。"""
    __tablename__ = "price_alerts"
    id: int | None = primary_key
    stock_id: int (fk, index)
    journal_id: int | None (fk)
    alert_type: str        # TARGET | STOP
    threshold: Decimal     # 触发价位
    triggered_price: Decimal
    triggered_at: datetime
    is_read: bool = False
    dedup_key: str (unique index)  # f"{stock_id}:{alert_type}:{threshold}" 去重
```

迁移：新增一个 Alembic version 建上述 4 张表（参考既有 `add_watchlist`/`add_financials` 写法）。在 `models/__init__.py` 集中导入以注册 metadata。

### 2. 筛选引擎（`backend/app/services/screener/engine.py`）

纯确定性，无 AI。

```python
# 支持字段 → 取值来源
FIELD_RESOLVERS = {
  "pe": from Financial.pe,
  "pb": from Financial.pb,
  "roe": Financial.roe,            # 小数
  "revenue_yoy": Financial.revenue_yoy,
  "profit_yoy": Financial.profit_yoy,
  "dividend_yield": Financial.dividend_yield,
  "market": Stock.market,          # 字符串等值
  "industry": Stock.industry,
  "in_watchlist": bool,
  "in_holdings": bool,
}
OPERATORS = {"<","<=",">",">=","=","between"}

@dataclass
class ScreenHit:
    stock_id: int; symbol: str; name: str; market: str
    matched: dict[str, str]   # field -> value(展示)
    missing: list[str]        # 数据缺失的字段

def run_screen(session, conditions, markets=None) -> list[ScreenHit]:
    # 1. 候选 = 已登记 stocks（可按 markets 过滤）
    # 2. 预取每只最新 Financial + watchlist/holdings 集合
    # 3. 对每只逐条件判定：缺字段→不满足且记入 missing；AND 组合
    # 4. 返回命中 + matched 值 + 规则原文(由 API 回显)
```

判定规则：百分比类字段（roe/revenue_yoy/profit_yoy/dividend_yield）库内存小数（0.15=15%），规则输入按"百分数"语义，引擎内部 ×100 比较或在 UI 注明；**统一约定规则里 `revenue_yoy > 15` 表示 15%**，引擎将库值 ×100 再比较。缺失字段 → 该条件 False 并加入 `missing`。

### 3. 日报服务（`backend/app/services/insights/daily_report.py`）

```python
def build_daily_report(session, market, config, on_date=None) -> InsightDocument:
    """组装上下文 → 调 AI → 存文档；失败降级。"""
    ctx = build_report_context(session, market, config, on_date)  # 全部数字代码算
    if not ai_client.is_available() or budget_exceeded:
        body = render_mechanical_md(ctx)          # 仅机械汇总
        degraded = True
    else:
        ai_text = ai_client.analyze(prompt_type="DAILY_REPORT", system=..., user=render_prompt(ctx,config))
        body = compose_md(ctx, ai_text)           # 机械数据 + AI 叙述
    upsert_document(DAILY_REPORT, market, on_date, body, ...)  # 按(type,market,date)幂等
```

`build_report_context` 复用：
- 市场概览：基准指数（`DEFAULT_BENCHMARKS[market]`）最近两日 close 算涨跌幅（同 benchmark 服务的数据获取方式）。
- 异动：遍历持仓+关注标的，用 `Price` 最近两日算日涨跌幅，超 `move_threshold_pct` 入列。
- 触价：对每只持仓/关注，找其关联 `Journal` 的 target/stop，与最新价比对。
- 决策日志对照：复用 `context_builder` 的精确数值（持仓成本/权重/journal 摘要）。
- 待办：`reminders.compute_reminders` + 集中度（持仓权重 >20%）。

`render_prompt` 注入 config：`focus_text`、`constraints`、`tone`、`detail_level`、`language`。系统提示沿用 `SYSTEM_BASE`（不预测、不荐股、数字不得编造）。

AI 提示要点（新增 `prompts.py` 模板 `DAILY_REPORT`）：
- 输入：已组装好的机械上下文（Markdown 片段）。
- 任务：用 {language} 写一份结构化日报叙述，侧重 {focus_text}，遵守 {constraints}，语气 {tone}，详略 {detail_level}。
- 红线：不预测股价、不给买卖信号、只用给定数字。

### 4. 筛选点评服务（`backend/app/services/insights/screener_review.py`）

```python
def review_hits(session, hits, language) -> InsightDocument:
    ctx = build_screener_context(session, hits)   # 每标的：精确财务+价格快照
    ai_text = ai_client.analyze(prompt_type="SCREENER_REVIEW", ...)  # 多空/风险/待调研
    body = compose_screener_md(ctx, ai_text)
    save InsightDocument(SCREENER_REVIEW, ...)
```

新增 prompt `SCREENER_REVIEW`：对每个标的给「多方观点 / 空方观点 / 主要风险 / 待补充调研」，**显式禁止**买卖结论与目标价；附免责声明。

### 5. 价格提醒（`backend/app/services/insights/price_alerts.py`）

```python
def evaluate_price_alerts(session) -> list[PriceAlert]:
    # 对每只"持仓∪关注"标的：
    #   取关联 journal 的 target_price / stop_loss_price
    #   取最新 close
    #   TARGET: 最新价 >= target → 触发；STOP: 最新价 <= stop → 触发
    #   dedup_key 去重（同标的同类型同价位只提醒一次，除非价位变更）
    # 新触发的写入 PriceAlert(is_read=False)
```

调度：在每次行情同步任务结束后调用一次（hook 进现有 `_run_market_sync` 之后），也提供手动触发与按需读取。

### 6. 调度集成（`backend/app/services/data_sync/scheduler.py` 扩展）

新增 jobs（沿用 `BackgroundScheduler`，时区 Asia/Tokyo）：
- 每市场日报：读取 `ReportConfig.schedule[market]` 动态注册 cron。配置变更时重建 jobs（提供 `reschedule_reports()`）。
- 每日清理：`cron(hour=4)` 调 `purge_old_documents(days=90)`。
- 价格提醒：复用市场同步 job，在其后调用 `evaluate_price_alerts`。

`ENABLE_SCHEDULER=false` 时不自动跑，但手动 API 仍可用。

### 7. 股票池扩充（`backend/scripts/seed_universe.py` + admin API）

- 预置成分股清单（精选，避免一次几千只压垮 SQLite/数据源）：US 标普精选 + 纳指龙头、CN 沪深300 部分、HK 主板蓝筹、JP 日经核心，每市场数十只，合计约 150–250 只。
- 复用 `_register`（discovery 的 MARKET_CURRENCY）+ `sync_stock_prices` + `fetch_financials`，分批、带重试、失败跳过、不重复登记（symbol+market 唯一）。
- admin API `POST /admin/seed-universe?market=&sync=`：后台任务执行，返回受理；进度通过 `sync_logs` 与文档完备度查询观测。
- 数据完备度：`GET /admin/universe-status` 返回每市场 已登记/有行情/有财务 计数。

### 8. API（统一响应壳，`/api/v1`）

`api/insights.py`：
- `GET /insights/documents?type=&market=&page=&page_size=` 列表（分页、倒序）
- `GET /insights/documents/{id}` 详情
- `GET /insights/documents/{id}/download` 返回 `text/markdown` 附件
- `POST /insights/documents/{id}/read` 标记已读
- `GET /insights/config` / `PUT /insights/config` 日报配置
- `POST /insights/daily/generate?market=` 手动生成（后台任务）
- `GET /insights/unread-count` 未读日报数（顶栏用）

`api/screener.py`：
- `GET/POST/PUT/DELETE /screener/rules` 规则 CRUD
- `POST /screener/run`（body: conditions/markets）执行筛选（同步返回命中）
- `POST /screener/review`（body: hits 或 rule_id）请求 AI 点评（后台任务，存文档）

`api/admin.py` 扩展：
- `POST /admin/seed-universe`、`GET /admin/universe-status`

`api/alerts.py`（或并入 reports）：
- `GET /alerts/price` 价格提醒列表（未读优先）
- `POST /alerts/price/{id}/read`、`POST /alerts/price/evaluate` 手动评估

### 9. 前端

新增页面（App Router）：
- `app/insights/page.tsx`：文档列表（类型/市场过滤、分页、未读标记、下载按钮）
- `app/insights/[id]/page.tsx`：Markdown 详情（安全渲染 + 下载）
- `app/insights/config/page.tsx`：日报配置表单（市场多选/时间/阈值/语气/语言/重点关注/约束）
- `app/insights/screener/page.tsx`：规则构建器 + 运行结果表 + "请 AI 点评"→ 跳详情

Markdown 渲染：用 `react-markdown` + `remark-gfm`（表格/删除线）+ `rehype-sanitize`（XSS 净化）。本平台个股链接：约定 AI/模板输出 `/stocks/{id}` 链接，sanitize 白名单放行同源相对链接。

侧栏：新增 "AI 洞察" 分组（日报 / 筛选）。命令面板补充导航项。

顶栏铃铛：现有 `useReviewReminders` 旁新增 `usePriceAlerts`，未读计数合并；下拉/跳转复用现有交互。新增 `useUnreadInsights` 给"AI 洞察"入口加未读点。

i18n：在 `messages.ts` 增加 `insights.*` / `screener.*` / `alerts.*` 三语键。

依赖：前端新增 `react-markdown`、`remark-gfm`、`rehype-sanitize`（写入 package.json，构建时 `npm ci` 安装）。

---

## Data Models

ER（新增部分）：

```
stocks(1) ──< price_alerts >── journals(0..1)
report_configs (单行, id=1)
screener_rules (多行)
insight_documents (多行) ── source_ref → report_configs / screener_rules (软引用, JSON)
```

字段精度沿用既有约定：金额/比率用 `DecimalString`（TEXT 存 Decimal），JSON 列用 `sa_column=Column(JSON)`，时间默认 `utcnow`。

---

## Error Handling

| 场景 | 处理 |
|------|------|
| AI 无 Key / 超预算 / 网络失败 | 日报/点评走降级：仅机械数据 + `degraded=True` + 原因；不抛错 |
| 某市场无持仓/关注/行情 | 生成"无重点事项"简报，不报错 |
| 筛选字段缺失 | 该条件判 False，记 `missing`，不报错 |
| 同市场同日重复触发日报 | 按 (type,market,date) UPSERT 幂等，返回既有/更新 |
| 成分股导入单只失败 | 记日志跳过，不影响其余，symbol+market 唯一防重复 |
| Markdown 含危险 HTML/脚本 | `rehype-sanitize` 白名单净化 |
| 价格提醒重复 | `dedup_key` 唯一约束去重 |
| 配置改了时间 | `reschedule_reports()` 重建 job，无需重启 |

---

## Testing Strategy

- **单元（后端，pytest）**：
  - 筛选引擎：各运算符、AND 组合、缺字段、百分比换算、in_watchlist/in_holdings。
  - 日报上下文：异动阈值、触价判定、空数据简报、数字来自代码。
  - 价格提醒：TARGET/STOP 触发与 dedup。
  - 文档清理：90 天边界。
  - 降级路径：无 Key 时仍产出文档且 `degraded=True`。
- **集成**：API 走 TestClient，校验统一响应壳、分页、下载 content-type、配置 CRUD、筛选 run/review。
- **构建校验**：后端 `python -c import` 冒烟 + `pytest`；前端 `tsc --noEmit` + `next build`。
- **部署后**：服务器健康检查、关键页面 HTTP 200、手动触发一篇日报与一次筛选验证端到端。

---

## 实施顺序（指导 tasks）

1. 模型 + 迁移 + `models/__init__` 注册
2. 筛选引擎（纯函数，先可测）
3. 日报上下文 + 提示 + 服务（含降级）
4. 价格提醒服务
5. 文档清理
6. API（insights / screener / alerts / admin 扩展）
7. 调度集成（日报 cron + 清理 + 同步后评估提醒）
8. 股票池扩充脚本 + admin
9. 前端：依赖、i18n、列表/详情/配置/筛选页、侧栏、顶栏铃铛聚合
10. 验证、提交、部署、服务器冒烟

---

## Correctness Properties

以下为可验证的核心正确性约束（指导测试与实现）：

### Property 1: 筛选确定性
`run_screen` 对相同输入（库状态 + 规则）必产生相同输出，且执行路径中不发起任何 AI/网络调用。
**Validates: Requirements 5.7, 5.5**

### Property 2: 数字不可由 AI 编造
日报与点评中所有个股数值均来自 `context_builder`/服务计算并注入提示；AI 仅产叙述，提示中明确"只用给定数字"。
**Validates: Requirements 2.5, 6.5**

### Property 3: AI 合规红线
点评与日报禁止输出买卖结论与价格预测；所有 AI 文档附免责声明（沿用 `DISCLAIMER`）。
**Validates: Requirements 6.2, 6.3, 9.2**

### Property 4: 日报幂等
对同一 `(doc_type=DAILY_REPORT, market, report_date)` 多次生成不产生重复行（UPSERT 覆盖）。
**Validates: Requirements 4.3**

### Property 5: 降级完整性
AI 不可用时仍返回含机械数据的有效文档，`degraded=True` 且 `degraded_reason` 非空。
**Validates: Requirements 4.5, 9.3**

### Property 6: 预算单调
每次实际 AI 调用都经 `BudgetGuard`，月度累计 token/成本只增不减且与 `ai_insights` 口径一致。
**Validates: Requirements 4.6, 6.6, 7.5**

### Property 7: 价格提醒去重
同一 `dedup_key` 至多存在一条未被新价位替代的提醒，刷新/重复评估不产生重复。
**Validates: Requirements 11.4**

### Property 8: 保留窗口
清理后不存在 `created_at < now-90d` 的 `insight_documents`；未超期文档不被删除。
**Validates: Requirements 7.6**

### Property 9: 缺失字段安全
筛选中缺失字段的标的不会被误判为满足条件，且必出现在该条件的 `missing` 中。
**Validates: Requirements 5.4**

### Property 10: 导入幂等
成分股批量导入对已存在的 `(symbol, market)` 不重复登记。
**Validates: Requirements 10.6**




