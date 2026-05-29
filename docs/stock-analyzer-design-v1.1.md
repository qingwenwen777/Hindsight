# 个人股票分析网站 — 项目设计文档

> 一个面向个人投资者的股票分析、记录与复盘平台。
> 核心目标：**学习投资 + 对抗认知偏差**，深度集成 AI 作为"投资教练"。

| | |
|---|---|
| 文档版本 | v1.1 |
| 上一版本 | v1.0 (2026-05-08) |
| 最后更新 | 2026-05-29 |
| 变更摘要 | 修正金额存储/拆股/公司行动模型；统一成本口径；新增完整前端设计规范（TradingView 风格） |

---

## 目录

1. [项目概述](#1-项目概述)
2. [需求分析](#2-需求分析)
3. [系统架构](#3-系统架构)
4. [数据库设计](#4-数据库设计)
5. [功能模块详细设计](#5-功能模块详细设计)
6. [API 设计](#6-api-设计)
7. [关键实现要点](#7-关键实现要点)
8. [前端设计规范](#8-前端设计规范)
9. [部署运维](#9-部署运维)
10. [实施路线图](#10-实施路线图)
11. [风险与应对](#11-风险与应对)
12. [附录](#12-附录)

---

## 1. 项目概述

### 1.1 项目背景

普通投资者面临三个核心痛点：

- **决策无记录**：买卖凭感觉，事后无法复盘，同一个错误反复犯。
- **数据散落**：行情在券商、财报在财经网站、想法在备忘录，无法整合分析。
- **认知偏差未被对抗**：事后合理化、确认偏误、过度自信等行为偏差，在没有外部反馈时几乎无法自我察觉。

本项目通过 **结构化记录 + 自动化分析 + AI 复盘** 的组合，把投资从"凭感觉"转变为"可学习、可改进的过程"。

### 1.2 项目目标

**核心目标**

- 把每一次交易都变成可量化、可复盘的学习样本。
- 用 AI 当"投资教练"，做定性分析和模式识别，而非预测股价。
- 通过产品设计主动对抗使用者（自己）的认知偏差。

**非目标（明确不做）**

- 不做实时高频交易系统（日线粒度足够）。
- 不做股价预测、买卖信号推荐。
- 不做多用户 SaaS，只服务自己。
- 不做对接券商下单（纯记录与分析）。

### 1.3 核心价值对比

| 维度 | 笔记 / Excel | 券商 App | 本项目 |
|---|---|---|---|
| 决策原因记录 | 自由文本 | 不支持 | 结构化字段 + 强制填写 |
| 跨市场统一视图 | 手动汇总 | 不支持 | 多币种自动换算 |
| 基准对比 | 无 | 部分 | 每笔 + 整体 alpha |
| AI 复盘 | 无 | 无 | 基于个人历史的 coach |
| 认知偏差防御 | 无 | 无 | 冷静期、锁定、告警 |
| 数据所有权 | 自己 | 平台 | 完全本地 |

---

## 2. 需求分析

### 2.1 功能性需求

#### F1 数据同步
- **F1.1** 多市场行情：A 股、港股、美股、日股（优先级 A 股 > 美股 > 港股 > 日股）。
- **F1.2** 每日定时同步关注列表 + 持仓股的日线 OHLCV。
- **F1.3** 复权处理（默认前复权）。
- **F1.4** 财报核心指标 + 估值数据。
- **F1.5** 汇率数据（USD / JPY / CNY / HKD）。
- **F1.6** 失败重试 + 告警。

#### F2 交易与持仓
- **F2.1** 手动录入买入 / 卖出。
- **F2.2** 交易类型：买入、卖出、分红、拆股、配股。
- **F2.3** 自动按市场规则计算手续费。
- **F2.4** 券商 CSV 批量导入（富途、雪球、IBKR、楽天）。
- **F2.5** 持仓自动从交易流水推导。
- **F2.6** 已实现盈亏（**FIFO 为账面口径**，加权平均仅作展示）。
- **F2.7** 浮动盈亏。
- **F2.8** 多币种统一基准展示（JPY / USD / CNY 可选）。

#### F3 现金流
- **F3.1** 入金、出金、汇款、分红、利息。
- **F3.2** 多币种现金账户。
- **F3.3** 时间加权收益率（TWR）。
- **F3.4** 内部收益率（IRR）。

#### F4 投资日志
- **F4.1** 每笔交易强制关联决策日志。
- **F4.2** 结构化字段：决策类型、预期持有时间、止损位、目标位、退出条件、信心评分（1–5）、决策时情绪。
- **F4.3** 提交后锁定不可修改，只能追加复盘。
- **F4.4** 30 / 60 / 90 天复盘提醒。
- **F4.5** 标签系统。

#### F5 数据分析
- **F5.1** 技术指标：MA、EMA、MACD、RSI、布林带、KDJ。
- **F5.2** 收益指标：总收益、年化、TWR、IRR、最大回撤、夏普、卡玛。
- **F5.3** 基准对比（A 股 / 沪深 300，美股 / SPX，港股 / HSI，日股 / N225）。
- **F5.4** 行业、市场、币种维度暴露。
- **F5.5** 集中度指标。
- **F5.6** 胜率、盈亏比、持有时间分布。

#### F6 AI 分析
- **F6.1** 单笔交易复盘。
- **F6.2** 财报摘要。
- **F6.3** 同行对比。
- **F6.4** 魔鬼代言人模式（找反方观点）。
- **F6.5** 失败模式识别（季度任务）。
- **F6.6** 自由对话（基于个人持仓和日志）。
- **F6.7** 模型分级 + 缓存 + 月度预算。

#### F7 认知偏差防御
- **F7.1** 日志锁定。
- **F7.2** 冷静期（30 秒倒计时）。
- **F7.3** 持有时间警告。
- **F7.4** 集中度告警（单股 > 20%、单行业 > 40%）。
- **F7.5** 情绪标记审计（不同情绪下的胜率统计）。

#### F8 可视化
- **F8.1** 仪表盘：总资产、当日 P&L、持仓分布、净值 vs 基准曲线。
- **F8.2** K 线图（技术指标叠加）。
- **F8.3** 持仓详情页。
- **F8.4** 月度 / 季度 / 年度复盘报表。
- **F8.5** 失败案例库。

### 2.2 非功能性需求

| 类别 | 要求 |
|---|---|
| 性能 | 仪表盘 < 2s；持仓查询 < 500ms；K 线 < 1s |
| 数据规模 | 5000 股 × 10 年 ≈ 1500 万行；1 万笔交易 |
| 可用性 | 单机本地 99%；每日自动备份 |
| 安全 | 数据本地；Web 密码登录（HTTPS + 会话）；备份加密 |
| 成本 | 数据源免费优先；AI 月度硬上限可配（建议 2000–3000 JPY） |
| 可扩展性 | 平滑迁移到 PostgreSQL；前端可独立部署 |

---

## 3. 系统架构

### 3.1 四层架构

```
┌──────────────────────────────────────────────────────┐
│  ① 数据源层                                            │
│  AKShare │ yfinance │ Alpha Vantage │ 财经新闻         │
└──────────────────────────────────────────────────────┘
                         ↓
┌──────────────────────────────────────────────────────┐
│  ② 后端服务层 (FastAPI)                                │
│  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐                  │
│  │同步  │ │分析  │ │AI    │ │业务  │                  │
│  │Sched │ │pandas│ │Claude│ │REST  │                  │
│  └──────┘ └──────┘ └──────┘ └──────┘                  │
└──────────────────────────────────────────────────────┘
                         ↓
┌──────────────────────────────────────────────────────┐
│  ③ 数据存储层                                          │
│  SQLite (主库) │ 文件缓存 (parquet / AI 上下文)         │
└──────────────────────────────────────────────────────┘
                         ↓
┌──────────────────────────────────────────────────────┐
│  ④ 前端层 (Next.js)                                    │
│  仪表盘 │ 持仓 │ 交易 │ 日志 │ 分析 │ AI │ 设置          │
└──────────────────────────────────────────────────────┘
```

### 3.2 技术栈

**后端**

| 组件 | 选型 | 理由 |
|---|---|---|
| 语言 | Python 3.11+ | 金融数据生态成熟 |
| Web | FastAPI | 异步、自动 OpenAPI |
| ORM | SQLModel | 类型安全 |
| 数据 | pandas + numpy | 行业标准 |
| 指标 | pandas-ta | 易装，功能足够 |
| 行情 | AKShare + yfinance | 免费、覆盖广 |
| 调度 | APScheduler | 嵌入式，免单独部署 |
| HTTP | httpx | 原生 async |
| AI | anthropic SDK | 官方 |
| 日志 | structlog | 结构化 |
| 测试 | pytest | 标准 |

**前端**

| 组件 | 选型 | 理由 |
|---|---|---|
| 框架 | Next.js 14 (App Router) | 生态最佳 |
| 语言 | TypeScript | 类型安全 |
| 样式 | Tailwind + shadcn/ui | 快速搭建 |
| 状态 | TanStack Query + Zustand | 服务端 + 客户端分离 |
| 图表 | **lightweight-charts**（K 线） + Recharts（简单图） | 见下方说明 |
| 表单 | react-hook-form + zod | 类型安全校验 |

> **图表库调整**：原方案用 ECharts 画 K 线没问题，但既然 UI 要做成 TradingView 风格，强烈建议 K 线直接用 TradingView 官方开源的 **lightweight-charts**。它就是 TradingView 同款渲染引擎的轻量版，体积约 45KB，交互手感（十字光标、缩放、平移）原生就是那个味道，省掉大量调样式的功夫。复杂的指标叠加 / 多面板（MACD、RSI 副图）它也原生支持。ECharts 作为备选保留。

**存储**

| 组件 | 选型 |
|---|---|
| 主库 | SQLite (WAL) → 升级 PostgreSQL |
| 缓存 | 进程内 LRU + 文件 (parquet) |

### 3.3 项目结构

```
stock-analyzer/
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI 入口
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── models/                  # SQLModel
│   │   │   ├── stock.py
│   │   │   ├── transaction.py
│   │   │   ├── corporate_action.py  # 新增：拆股/送股/配股
│   │   │   ├── journal.py
│   │   │   ├── cash_flow.py
│   │   │   └── ai_insight.py
│   │   ├── api/                     # REST endpoints
│   │   │   ├── stocks.py
│   │   │   ├── transactions.py
│   │   │   ├── journals.py
│   │   │   ├── analytics.py
│   │   │   └── ai.py
│   │   ├── services/
│   │   │   ├── data_sync/
│   │   │   │   ├── akshare_client.py
│   │   │   │   ├── yfinance_client.py
│   │   │   │   └── scheduler.py
│   │   │   ├── analysis/
│   │   │   │   ├── pnl.py           # 盈亏 (FIFO)
│   │   │   │   ├── returns.py       # TWR / IRR
│   │   │   │   ├── indicators.py
│   │   │   │   ├── benchmark.py
│   │   │   │   └── risk.py
│   │   │   ├── ai/
│   │   │   │   ├── client.py
│   │   │   │   ├── prompts.py
│   │   │   │   ├── context_builder.py
│   │   │   │   └── budget.py
│   │   │   └── biases/
│   │   │       ├── concentration.py
│   │   │       └── cooling_period.py
│   │   ├── core/
│   │   │   ├── money.py             # Decimal 金额类型
│   │   │   ├── currency.py
│   │   │   ├── adjust.py
│   │   │   └── fees.py
│   │   └── utils/
│   ├── tests/
│   ├── alembic/                     # DB 迁移
│   └── pyproject.toml
├── frontend/
│   ├── app/
│   │   ├── (dashboard)/
│   │   ├── (transactions)/
│   │   ├── (journal)/
│   │   ├── (analytics)/
│   │   └── (ai-chat)/
│   ├── components/
│   ├── lib/
│   └── package.json
├── data/
│   ├── stock.db
│   ├── backups/
│   └── exports/
└── docker-compose.yml
```

### 3.4 部署架构

- **起步方案**：本机 Docker → Tailscale 远程访问。手机也能用，数据不出公网。
- **进阶方案**：后端 Railway / 前端 Vercel / DB PostgreSQL，备份到 Cloudflare R2。

---

## 4. 数据库设计

> **v1.1 重要修正**
>
> 1. **金额一律不用 `DECIMAL`**。SQLite 没有真正的定点类型，`DECIMAL(20,4)` 会退化成浮点，金额累加产生误差。本文档所有金额 / 价格 / 数量字段统一用 `TEXT` 存储（Python 侧用 `Decimal` 解析），或在确定无小数的场景用 `INTEGER` 存最小单位。SQLModel 侧用自定义 `Decimal` 类型适配。
> 2. **公司行动（拆股 / 送股 / 配股）从 `transactions` 拆出**，单列 `corporate_actions` 表。买卖与公司行动语义不同，混在一张表会污染成本基础计算。
> 3. **分红不再当作 transaction**，记入 `cash_flows`（type=DIVIDEND）。
> 4. **持仓不建表**，由分析层用 Python 从 `transactions` + `corporate_actions` 计算（FIFO），不再用 SQL 视图算拆股（视图无法表达乘法型行动）。

### 4.1 实体关系

```
stocks ──1:N→ prices
stocks ──1:N→ transactions ──1:1→ journals ──1:N→ reviews
stocks ──1:N→ corporate_actions
cash_accounts ──1:N→ cash_flows ←── transactions
watchlist ──N:1→ stocks
ai_insights → stocks / transactions / journals / portfolio
```

### 4.2 核心表 SQL

#### stocks — 股票元信息

```sql
CREATE TABLE stocks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,              -- '600519' / 'AAPL' / '0700.HK'
    market TEXT NOT NULL,              -- 'CN' / 'US' / 'HK' / 'JP'
    name TEXT NOT NULL,
    name_en TEXT,
    industry TEXT,
    sector TEXT,
    currency TEXT NOT NULL,            -- 'CNY' / 'USD' / 'HKD' / 'JPY'
    listed_date DATE,
    delisted_date DATE,
    is_etf BOOLEAN DEFAULT 0,
    metadata JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(symbol, market)
);
CREATE INDEX idx_stocks_market ON stocks(market);
CREATE INDEX idx_stocks_industry ON stocks(industry);
```

#### prices — 日线行情（前复权）

```sql
CREATE TABLE prices (
    stock_id INTEGER NOT NULL,
    date DATE NOT NULL,
    open TEXT,                         -- Decimal 字符串
    high TEXT,
    low TEXT,
    close TEXT NOT NULL,
    volume BIGINT,
    turnover TEXT,
    adjust_factor TEXT,
    PRIMARY KEY (stock_id, date),
    FOREIGN KEY (stock_id) REFERENCES stocks(id)
);
CREATE INDEX idx_prices_date ON prices(date);
```

#### transactions — 交易流水（只放买/卖，最关键）

```sql
CREATE TABLE transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    stock_id INTEGER NOT NULL,
    type TEXT NOT NULL,                -- BUY / SELL  (仅买卖)
    trade_date DATE NOT NULL,
    quantity TEXT NOT NULL,            -- Decimal 字符串
    price TEXT NOT NULL,               -- 原币种成交价
    currency TEXT NOT NULL,
    fx_rate_to_jpy TEXT,               -- 当日汇率
    commission TEXT DEFAULT '0',
    tax TEXT DEFAULT '0',
    other_fees TEXT DEFAULT '0',
    journal_id INTEGER,
    is_imported BOOLEAN DEFAULT 0,     -- CSV 导入标记
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (stock_id) REFERENCES stocks(id),
    FOREIGN KEY (journal_id) REFERENCES journals(id)
);
CREATE INDEX idx_tx_stock_date ON transactions(stock_id, trade_date);
CREATE INDEX idx_tx_date ON transactions(trade_date);
```

> **持仓不建表**，从 `transactions` + `corporate_actions` 实时计算，避免数据不一致。

#### corporate_actions — 公司行动（新增）

```sql
CREATE TABLE corporate_actions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    stock_id INTEGER NOT NULL,
    action_type TEXT NOT NULL,         -- SPLIT / BONUS / RIGHTS / MERGE
    ex_date DATE NOT NULL,             -- 除权除息日
    -- 拆股/送股：持股数乘以 ratio_num/ratio_den（如 10送10 = 2/1）
    ratio_num TEXT,
    ratio_den TEXT,
    -- 配股：按比例可认购，认购价
    subscribe_ratio TEXT,
    subscribe_price TEXT,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (stock_id) REFERENCES stocks(id)
);
CREATE INDEX idx_ca_stock_date ON corporate_actions(stock_id, ex_date);
```

#### journals — 决策日志

```sql
CREATE TABLE journals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    stock_id INTEGER NOT NULL,
    decision_type TEXT NOT NULL,       -- BUY / SELL / HOLD / WATCH
    -- 结构化
    thesis_category TEXT,              -- VALUATION / TREND / EVENT / GROWTH / OTHER
    expected_horizon TEXT,             -- SHORT / MEDIUM / LONG
    target_price TEXT,
    stop_loss_price TEXT,
    exit_condition TEXT,
    confidence INTEGER,                -- 1-5
    emotion TEXT,                      -- CALM / HESITANT / FOMO / PANIC / REVENGE
    -- 自由文本
    thesis TEXT NOT NULL,
    risks TEXT,
    tags JSON,
    -- 锁定
    is_locked BOOLEAN DEFAULT 0,
    locked_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (stock_id) REFERENCES stocks(id)
);
```

#### reviews — 事后复盘

```sql
CREATE TABLE reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    journal_id INTEGER NOT NULL,
    review_date DATE NOT NULL,
    days_since_decision INTEGER,
    price_at_review TEXT,
    pnl_pct TEXT,
    benchmark_pnl_pct TEXT,
    thesis_held BOOLEAN,
    luck_vs_skill TEXT,                -- SKILL / LUCK / MIXED
    lessons TEXT,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (journal_id) REFERENCES journals(id)
);
```

#### cash_accounts + cash_flows

```sql
CREATE TABLE cash_accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,                -- '富途港股' / 'IBKR 美股'
    broker TEXT,
    currency TEXT NOT NULL,
    notes TEXT
);

CREATE TABLE cash_flows (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id INTEGER NOT NULL,
    flow_date DATE NOT NULL,
    type TEXT NOT NULL,                -- DEPOSIT/WITHDRAW/DIVIDEND/INTEREST/TRADE_BUY/TRADE_SELL/FEE/TAX/FX
    amount TEXT NOT NULL,              -- 正=入,负=出 (Decimal 字符串)
    currency TEXT NOT NULL,
    fx_rate_to_jpy TEXT,
    related_tx_id INTEGER,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (account_id) REFERENCES cash_accounts(id),
    FOREIGN KEY (related_tx_id) REFERENCES transactions(id)
);
CREATE INDEX idx_cf_account_date ON cash_flows(account_id, flow_date);
```

#### ai_insights — AI 分析缓存

```sql
CREATE TABLE ai_insights (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    target_type TEXT NOT NULL,         -- STOCK / TRANSACTION / JOURNAL / PORTFOLIO
    target_id INTEGER,
    prompt_type TEXT NOT NULL,         -- TRADE_REVIEW / EARNINGS_SUMMARY / ...
    input_hash TEXT NOT NULL,
    model TEXT NOT NULL,
    prompt_tokens INTEGER,
    completion_tokens INTEGER,
    cost_jpy TEXT,
    response TEXT NOT NULL,
    metadata JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_ai_target ON ai_insights(target_type, target_id);
CREATE INDEX idx_ai_hash ON ai_insights(input_hash);
```

#### fx_rates + fee_rules + watchlist

```sql
CREATE TABLE fx_rates (
    date DATE NOT NULL,
    base_currency TEXT NOT NULL,
    quote_currency TEXT NOT NULL,
    rate TEXT NOT NULL,
    PRIMARY KEY (date, base_currency, quote_currency)
);

CREATE TABLE fee_rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    market TEXT NOT NULL,
    broker TEXT,
    direction TEXT,                    -- BUY / SELL / BOTH
    fee_type TEXT NOT NULL,            -- COMMISSION / STAMP / SEC_FEE / ...
    rate TEXT,
    min_amount TEXT,
    fixed_amount TEXT,
    effective_from DATE NOT NULL,
    effective_to DATE
);

CREATE TABLE watchlist (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    stock_id INTEGER NOT NULL UNIQUE,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    notes TEXT,
    tags JSON,
    FOREIGN KEY (stock_id) REFERENCES stocks(id)
);
```

### 4.3 持仓计算（取代 v_holdings 视图）

持仓由分析层计算，伪代码：

```python
def compute_holdings(stock_id) -> Holding:
    events = load_events(stock_id)          # transactions + corporate_actions, 按日期排序
    shares = Decimal(0)
    fifo_lots = []                          # [(剩余股数, 单股成本)]
    for e in events:
        if e.kind == "BUY":
            cost_per_share = (e.quantity * e.price + e.fees) / e.quantity
            fifo_lots.append([e.quantity, cost_per_share])
            shares += e.quantity
        elif e.kind == "SELL":
            shares -= e.quantity            # 从 FIFO 队首扣除
            consume_fifo(fifo_lots, e.quantity)
        elif e.kind == "SPLIT" or e.kind == "BONUS":
            ratio = e.ratio_num / e.ratio_den       # 乘法型
            shares *= ratio
            for lot in fifo_lots:
                lot[0] *= ratio
                lot[1] /= ratio                     # 单股成本相应稀释
    return Holding(shares=shares, cost_basis=sum(l[0]*l[1] for l in fifo_lots))
```

> **成本口径钦定**：FIFO 为账面 / 报税口径，加权平均仅在 UI 上作为"参考均价"展示，两者并存但不混用。

---

## 5. 功能模块详细设计

### 5.1 数据同步

**调度时间表（JST）**

| 任务 | 时间 |
|---|---|
| A 股日线 | 每交易日 16:30 |
| 港股日线 | 每交易日 17:30 |
| 美股日线 | 次日 06:30 |
| 日股日线 | 每交易日 16:00 |
| 汇率 | 每日 09:00 |
| 财报指标 | 每周六 10:00 |
| 持仓估值更新 | 盘中每小时 |

**同步流程**

1. 查需要同步的股票（关注 + 持仓 + ETF 基准）。
2. 检查 `prices` 表的最新日期（增量同步）。
3. 调用数据源 API（批量，带重试）。
4. 数据校验：价格非负、`high >= low`、open/close 在区间内。
5. 复权处理：前复权。
6. UPSERT 到 `prices`。
7. 记录同步日志。
8. 失败 > 5% 触发告警。

**容错优先级**

```
A 股: AKShare → Tushare → 失败标记
港股: AKShare → yfinance → 失败标记
美股: yfinance → AKShare → Alpha Vantage → 失败标记
日股: yfinance → 失败标记
```

### 5.2 交易管理

**录入流程（强制日志 + 冷静期）**

```
点击"录入交易"
   ↓
Step 1: 交易信息(股票、方向、数量、价格、日期)
   ↓
Step 2: 决策日志(必填)
   ↓
冷静期 30 秒倒计时(可取消)
   ↓
提交事务:
  1. 写 journals(is_locked=true)
  2. 写 transactions(关联 journal_id)
  3. 写 cash_flows(对应账户扣款)
  4. 失效持仓缓存
  5. 异步触发 AI 分析(可选)
   ↓
弹"已记录" + 30 天后复盘提醒
```

**CSV 导入**：支持富途、雪球、IBKR、楽天証券格式。流程为 上传 → 自动检测 → 字段映射 UI → 预览 → 批量写入。导入的交易自动创建占位 journal，标记 `is_imported=true`，允许后期补写。

### 5.3 投资日志

**锁定机制**

```python
def submit_journal(journal):
    journal.is_locked = True
    journal.locked_at = now()
    db.commit()
    # 中间件层拦截后续 UPDATE

def add_review(journal_id, review):
    # INSERT 到 reviews,不动 journal 本体
    db.add(review)
```

**复盘提醒**：每天后台扫描距决策 30 / 60 / 90 / 180 / 365 天的日志，缺 review 就推送通知（浏览器 / Telegram）。

### 5.4 分析引擎

**FIFO 盈亏**

```python
def calculate_realized_pnl(stock_id) -> Decimal:
    """
    1. 取所有 BUY/SELL 按 trade_date 排序(公司行动同步调整)
    2. 维护 FIFO 队列(剩余股数, 单股成本)
    3. BUY → 入队
    4. SELL → 队首扣除,算每笔盈亏
    5. 累加 - 总手续费 - 总税
    """
```

**TWR（时间加权，排除资金进出）**：按现金流事件切分时间段，每段独立算收益率，几何相乘。

```
TWR = ∏(1 + r_i) - 1
r_i = (期末市值 - 期初 - 该期净存入) / (期初 + 加权净存入)
```

**IRR（内部收益率）**：用 `scipy.optimize.brentq` 解。`cash_flows` 是 `[(日期, 金额)]`，入金为负、出金为正，加上当前市值作为最终现金流入。

**基准对比**

```python
def alpha_vs_benchmark(portfolio_returns, benchmark_symbol, period):
    """返回:组合收益、基准收益、alpha、信息比率、跟踪误差、β"""
```

| 市场 | 基准 |
|---|---|
| A 股 | 沪深 300（000300.SH） |
| 港股 | 恒生指数（HSI） |
| 美股 | S&P 500（^GSPC） |
| 日股 | 日经 225（^N225） |

### 5.5 AI 分析

**模型分级**

```python
TASK_MODEL_MAP = {
    "EARNINGS_SUMMARY":   HAIKU,    # 摘要
    "TAG_GENERATION":     HAIKU,
    "TRADE_REVIEW":       SONNET,   # 常规复盘
    "PEER_COMPARE":       SONNET,
    "DEVILS_ADVOCATE":    SONNET,
    "FAILURE_PATTERN":    SONNET,   # v1.1: 由 Opus 降级,控成本
    "QUARTERLY_REVIEW":   SONNET,   # v1.1: 同上,需要时手动升 Opus
}
```

> **预算调整**：原 1000 JPY/月对 Opus 长上下文偏紧。v1.1 默认将季度深度任务降到 Sonnet，月度硬上限建议设 2000–3000 JPY；需要 Opus 时在设置里手动开启单次升级。

**上下文组装（关键原则：数字由代码算，AI 只做定性）**

```python
def build_trade_review_context(transaction_id) -> str:
    tx = get_transaction(transaction_id)
    journal = tx.journal

    # 后续走势(代码精确计算)
    return_30d = calc_return(tx.stock_id, tx.trade_date, days=30)
    benchmark_30d = calc_benchmark_return(tx.stock.market, tx.trade_date, days=30)
    alpha = return_30d - benchmark_30d

    return f"""
## 交易信息
- 股票: {tx.stock.name} ({tx.stock.symbol})
- 方向: {tx.type} | 日期: {tx.trade_date}
- 价格: {tx.price} {tx.currency} | 数量: {tx.quantity}

## 决策日志(用户当时写的)
- 类型: {journal.thesis_category}
- 预期持有: {journal.expected_horizon}
- 目标价: {journal.target_price} | 止损: {journal.stop_loss_price}
- 信心(1-5): {journal.confidence}
- 情绪: {journal.emotion}
- 主要逻辑: {journal.thesis}
- 主要风险: {journal.risks}

## 决策后实际走势(代码计算,精确)
- 30 天回报: {return_30d:+.2f}%
- 同期基准: {benchmark_30d:+.2f}%
- 超额收益: {alpha:+.2f}%

## 决策时财务数据
- 营收 YoY: {revenue_yoy:.1%}
- 净利 YoY: {profit_yoy:.1%}
- PE: {pe} | ROE(TTM): {roe}
"""
```

**Prompt 模板 1 — 交易复盘**

```
你是一位资深投资教练。下面是用户的一笔交易和决策日志,以及之后的实际走势。

请做三件事(每件 100 字以内):
1. 评估原始投资逻辑现在是否仍然成立(基于实际数据,不要使用训练数据中的信息)
2. 判断这笔交易的结果更多源自"运气"还是"判断力"
3. 指出用户决策记录中可能存在的认知偏差(过度自信、确认偏误、FOMO 等)

要求:
- 直接、简洁,无客套
- 不预测未来股价
- 引用数字必须来自下面的数据,不要自己编

数据如下:
{context}
```

**Prompt 模板 2 — 魔鬼代言人**

```
用户正在考虑以下投资决策:
{decision}

请扮演怀疑者,从三个角度找最强反方观点:
1. 这个逻辑哪里可能是错的?
2. 用户可能忽略了什么风险?
3. 哪些数据点与论点矛盾?

要求:
- 不平衡观点,你的任务就是找问题
- 每个反对意见必须具体、可验证
- 不使用训练数据中的具体数字
```

**Prompt 模板 3 — 失败模式识别（季度任务）**

```
以下是用户过去 3 个月所有亏损 > 5% 的交易及决策摘要:
{losing_trades_summary}

识别 2-3 个最显著的共性模式(不要凑数):
- 特定情绪下犯错更多?
- 特定决策类型胜率低?
- 预期与实际持有时间严重不符?
- 止损纪律差?

每个模式给出:
- 模式描述
- 支持的具体交易(列出 transaction_id)
- 一条具体可执行的改进建议
```

**缓存**：`input_hash = sha256(prompt_type + context)`，7 天内命中直接返回。

**预算**

```python
class BudgetGuard:
    monthly_budget_jpy = 2000  # 可配

    def can_call(self, estimated_cost):
        return self.used_this_month() + estimated_cost < self.monthly_budget_jpy

    def warn_if_close(self):
        if self.used_this_month() > self.monthly_budget_jpy * 0.8:
            notify("AI 月度预算已用 80%")
```

### 5.6 认知偏差防御

| 防御 | 触发 | 行为 |
|---|---|---|
| 冷静期 | 任何买卖提交前 | 30 秒倒计时,可取消 |
| 日志锁定 | 提交后 | DB 中间件拦截 UPDATE |
| 持有时间警告 | 声明 LONG 但 < 30 天卖 | 弹窗要求填"为什么改主意" |
| 集中度告警 | 单股 > 20% / 单行业 > 40% | 红色高亮 + 加仓弹窗 |
| 情绪审计 | 每月报表 | 展示不同情绪下胜率 |
| 复仇交易拦截 | 连续 3 次亏损后买同一股 | 冷静期延长到 5 分钟 + AI 确认 |

---

## 6. API 设计

REST 风格，前缀 `/api/v1`。

**股票**
```
GET    /stocks/search?q=&market=
GET    /stocks/{id}
GET    /stocks/{id}/prices?start=&end=
GET    /stocks/{id}/indicators?type=MACD,RSI
GET    /stocks/{id}/financials
```

**交易**
```
POST   /transactions
GET    /transactions?stock_id=&start=&end=&type=
GET    /transactions/{id}
DELETE /transactions/{id}      # 仅未锁定的占位记录
POST   /transactions/import
```

**日志**
```
POST   /journals
GET    /journals?stock_id=&type=&emotion=
GET    /journals/{id}
POST   /journals/{id}/reviews
GET    /journals/{id}/reviews
```

**组合**
```
GET    /portfolio/holdings
GET    /portfolio/summary?currency=JPY
GET    /portfolio/cash-flows?account_id=
GET    /portfolio/returns?period=YTD&type=TWR
GET    /portfolio/benchmark-comparison?period=YTD
GET    /portfolio/exposure?dimension=industry|market|currency
GET    /portfolio/concentration
```

**AI**
```
POST   /ai/analyze        body: { type: "TRADE_REVIEW", target_id: 123 }
GET    /ai/insights?target_type=&target_id=
POST   /ai/chat           body: { message: "...", context_ids: [...] }
GET    /ai/budget
```

**管理**
```
POST   /admin/sync/prices?market=CN
GET    /admin/sync/status
GET    /admin/sync/logs?date=
```

**报表**
```
GET    /reports/monthly?year=&month=
GET    /reports/quarterly?year=&quarter=
GET    /reports/failures
GET    /reports/emotion-audit
```

**统一响应壳**

```json
{
  "code": 0,
  "message": "ok",
  "data": { },
  "meta": { "page": 1, "total": 100 }
}
```

---

## 7. 关键实现要点

### 7.1 多币种处理

存储原币种 + 当时汇率，展示按基准换算。

```python
class Money:
    amount: Decimal
    currency: str

    def to(self, target_currency, on_date):
        if self.currency == target_currency:
            return self
        rate = get_fx_rate(self.currency, target_currency, on_date)
        return Money(self.amount * rate, target_currency)
```

汇率通过 yfinance 获取（`USDJPY=X` 等），缓存到 `fx_rates`。缺失日期回退到最近交易日，并标记 `is_estimated`。

### 7.2 复权处理

```python
# AKShare
ak.stock_zh_a_hist(symbol="600519", adjust="qfq")  # 前复权

# yfinance(默认复权)
yf.download("AAPL", auto_adjust=True)
```

数据库统一存前复权。如果用户输入的成本是原始价，单独存 `original_price` 字段做映射。

### 7.3 手续费引擎

```python
def calculate_fees(market, direction, amount, broker=None) -> Fees:
    rules = db.query(FeeRule).filter(...).all()
    commission = max(amount * rule.rate, rule.min_amount or 0)
    tax = amount * stamp_rate if direction == 'SELL' else 0
    ...
```

**预置规则**

```
A 股 BUY:  佣金 0.025%(最低 5 CNY)
A 股 SELL: 佣金 0.025% + 印花税 0.05% + 过户费 0.001%
港股:      佣金 0.0027% + 印花税 0.13% + 交易征费 0.0027%
美股 BUY:  佣金 0(IBKR 阶梯)或 1 USD(富途)
美股 SELL: 佣金 + SEC fee 0.00229% + FINRA fee 每股 0.000166
日股:      楽天証券默认 0.099% 含消费税
```

> 费率随政策变动（如 A 股印花税历史调整），用 `fee_rules.effective_from/to` 做版本化，按交易日匹配生效规则。

### 7.4 性能优化

- SQLite 用 WAL 模式允许并发读。
- 行情大量历史查询缓存为 parquet 文件。
- 持仓增量计算，交易写入失效缓存。
- K 线前端按可视区间懒加载。

### 7.5 备份

```bash
# 每日 02:00
sqlite3 data/stock.db ".backup data/backups/stock_$(date +%Y%m%d).db"
gzip data/backups/stock_$(date +%Y%m%d).db   # 保留 30 天
# 本地 + 加密上传 R2 / iCloud
# 每周一次完整 SQL dump
```

---

## 8. 前端设计规范

> 目标风格：**TradingView 式的极简、专业、信息密度高但不杂乱**。深色为默认，大量留白，等宽数字，克制的强调色。整体气质是"工具"，不是"App"——没有花哨动效、没有营销式色块、没有券商 App 那种信息过载和红绿满屏。

### 8.1 设计原则

1. **数据是主角，UI 是背景**。界面元素（边框、背景、图标）一律低调，让数字、图表、文字成为视觉焦点。
2. **克制用色**。颜色只用于传达信息（涨/跌、告警、状态），不用于装饰。一屏内强调色不超过两种。
3. **信息分层**。用字号、字重、颜色明度做层级，而不是用框和分割线堆叠。
4. **等宽数字对齐**。所有金额、百分比、价格用 tabular-nums，纵向严格对齐，方便扫读。
5. **响应即时**。数据切换、悬停、缩放无明显延迟感；加载用骨架屏而非 spinner。
6. **危险操作有摩擦**。删除、解锁、超预算调用 AI 等，二次确认。
7. **键盘友好**。搜索（`/`）、命令面板（`Cmd/Ctrl+K`）、页面快捷跳转。

### 8.2 设计系统（Design Tokens）

**配色 — 深色主题（默认）**

| 用途 | Token | 值 | 说明 |
|---|---|---|---|
| 页面背景 | `bg-base` | `#0B0E11` | 近黑、略带蓝灰 |
| 面板背景 | `bg-surface` | `#131722` | TradingView 同款深蓝灰 |
| 浮层背景 | `bg-elevated` | `#1C2230` | 卡片/弹窗 |
| 边框 | `border-subtle` | `#2A2E39` | 极低对比 |
| 主文字 | `text-primary` | `#D1D4DC` | 不用纯白，减轻刺眼 |
| 次文字 | `text-secondary` | `#787B86` | 标签、辅助 |
| 弱文字 | `text-muted` | `#4A4E5A` | 占位、禁用 |
| 强调/主色 | `accent` | `#2962FF` | TradingView 蓝，用于链接/选中/按钮 |
| 上涨 | `up` | `#26A69A` | 青绿（默认，可切换习惯）|
| 下跌 | `down` | `#EF5350` | 红 |
| 警告 | `warn` | `#FF9800` | 集中度/预算告警 |
| 危险 | `danger` | `#F23645` | 删除/解锁 |

**配色 — 浅色主题（可选）**

| 用途 | 值 |
|---|---|
| 页面背景 | `#FFFFFF` |
| 面板背景 | `#F8F9FD` |
| 边框 | `#E0E3EB` |
| 主文字 | `#131722` |
| 次文字 | `#787B86` |
| 主色 | `#2962FF` |

**涨跌色切换**：A 股习惯红涨绿跌，美/日/港习惯绿涨红跌。提供全局开关 `colorScheme: 'asia' | 'western'`，仅交换 `up`/`down` 的语义映射，组件内只引用语义 token（`up`/`down`），不硬编码红绿。

**字体**

| 用途 | 字体 |
|---|---|
| UI 文字 | `Inter` / 系统 sans（中文 `PingFang SC` / `Microsoft YaHei`） |
| 数字 / 价格 / 代码 | `JetBrains Mono` / `Roboto Mono`（开启 `tabular-nums`） |

**字号阶梯**

```
display  28px / 600   页面主数字(总资产)
h1       20px / 600   页面标题
h2       16px / 600   区块标题
body     14px / 400   正文(默认)
small    13px / 400   表格、标签
caption  12px / 400   辅助说明
mono-lg  18px / 500   关键数字
mono-sm  13px / 400   表格数字
```

**间距 / 圆角 / 阴影**

```
spacing  4 / 8 / 12 / 16 / 24 / 32 (px,8 基准)
radius   sm 4px / md 6px / lg 8px   (整体偏小,专业感)
shadow   仅浮层用,深色下用更深的背景而非阴影来分层
border   1px solid border-subtle,优先用背景明度差分层
```

**密度**：表格行高 36px（紧凑）/ 44px（舒适），默认紧凑。仪表盘卡片 padding 16px。

### 8.3 布局框架

```
┌────────────────────────────────────────────────────────────┐
│ Topbar  Logo │ 全局搜索(/)        基准币种▾  主题  通知  头像 │
├──────┬─────────────────────────────────────────────────────┤
│      │                                                      │
│ Side │   Page Content                                       │
│ Nav  │   (最大宽度不限,但内容区留白,关键区块网格对齐)        │
│ 56px │                                                      │
│ /    │                                                      │
│ 220px│                                                      │
│      │                                                      │
└──────┴─────────────────────────────────────────────────────┘
```

- **侧边导航**：默认折叠为 56px 图标栏，悬停或固定展开为 220px。分组：概览 / 交易 / 分析 / AI / 设置。
- **顶栏**：全局股票搜索（`/` 聚焦，下拉直达个股）、基准币种切换（JPY/USD/CNY）、主题切换、复盘提醒铃铛（带未读数）、设置入口。
- **命令面板**：`Cmd/Ctrl+K` 打开，快速跳转页面、搜股票、新建交易。

### 8.4 路由表

| 路由 | 页面 |
|---|---|
| `/` | 仪表盘 |
| `/portfolio` | 组合总览 |
| `/portfolio/holdings` | 持仓详情 |
| `/portfolio/cash` | 现金流 |
| `/stocks/[id]` | 个股详情（K 线主战场） |
| `/transactions` | 交易列表 |
| `/transactions/new` | 录入（两步 + 冷静期） |
| `/transactions/import` | 批量导入 |
| `/journals` | 日志列表 |
| `/journals/[id]` | 日志详情（含复盘） |
| `/analytics/returns` | 收益分析 |
| `/analytics/benchmark` | 基准对比 |
| `/analytics/exposure` | 暴露分析 |
| `/analytics/emotion` | 情绪审计 |
| `/ai/chat` | AI 对话 |
| `/ai/insights` | AI 洞察列表 |
| `/reports` | 报表中心 |
| `/watchlist` | 关注列表 |
| `/settings` | 设置 |

### 8.5 核心组件库

> 基于 shadcn/ui，按本设计系统重新定制 token。以下是项目特有的复合组件。

| 组件 | 说明 |
|---|---|
| `<Stat>` | 关键数字单元：label + 大号等宽数字 + 涨跌色 + 涨跌箭头 + 副值（如对比基准）。仪表盘核心。 |
| `<PnL>` | 盈亏文字，自动按 `colorScheme` 上色，带 `+/-` 号和 tabular-nums。 |
| `<PercentBadge>` | 百分比小标签（涨跌/超额收益），背景为对应色的 8% 透明度。 |
| `<CandleChart>` | lightweight-charts 封装，主图 K 线 + 成交量，可叠加 MA/EMA/布林带，副图 MACD/RSI/KDJ。支持买卖点 marker。 |
| `<EquityCurve>` | 净值 vs 基准面积/线图（Recharts 或 lightweight-charts line series）。 |
| `<DataTable>` | 紧凑表格：列排序、固定表头、右对齐数字列、行悬停高亮、可选行密度。 |
| `<DonutExposure>` | 暴露/集中度环形图，超阈值切片高亮警告色。 |
| `<EmotionPicker>` | 情绪选择（emoji + 文案：冷静 😐 / 犹豫 🤔 / FOMO 🤩 / 恐慌 😱 / 复仇 😤）。 |
| `<ConfidenceSlider>` | 1–5 信心评分，点选式。 |
| `<CooldownButton>` | 带 30 秒倒计时的提交按钮，倒计时中显示进度环 + 剩余秒数，可取消。 |
| `<LockBadge>` | 日志锁定标识（🔒 + locked_at），明示不可改。 |
| `<ConcentrationAlert>` | 集中度告警条，超阈值出现，警告色，附 AI 二次确认入口。 |
| `<AIInsightCard>` | AI 洞察卡片：模型徽章 + 生成时间 + 成本 + 内容（markdown）+ "AI 仅供参考"水印。 |

### 8.6 关键图表规格

**K 线（个股详情主图）— lightweight-charts**

- 主图：蜡烛图（涨跌色随 colorScheme），右侧价格轴，底部时间轴，十字光标。
- 叠加层（可勾选）：MA5/MA10/MA20/MA60、EMA、布林带（上中下三线 + 半透明带）。
- 成交量：主图底部独立子区，柱色随当日涨跌。
- 副图面板（可开关，独立窗格）：MACD（柱 + DIF/DEA 双线）、RSI（含 30/70 参考线）、KDJ。
- **买卖点标注**：用户自己的交易在对应日期打 marker（买=上箭头 up 色，卖=下箭头 down 色），悬停显示价格/数量/关联日志摘要。
- 交互：滚轮缩放、拖拽平移、双击复位；区间懒加载（仅请求可视范围 + 缓冲）。
- 工具条：周期切换（日/周/月）、复权切换（前/不复权）、指标管理、全屏。

**净值 vs 基准曲线**

- 两条线：组合净值（accent）、基准净值（text-secondary 虚线），归一化到起点 100。
- 可填充组合相对基准的超额收益区域（正 up 色、负 down 色，低透明度）。
- 悬停十字线联动两条线的数值 tooltip。
- 时间区间快捷切换：1M / 3M / 6M / YTD / 1Y / ALL。

**暴露 / 集中度环形图**

- 行业 / 市场 / 币种三个维度切换。
- 超阈值切片（单股 > 20% / 单行业 > 40%）用警告色描边 + 中心提示。
- 图例按占比降序，附百分比与金额。

### 8.7 逐页 UI 设计

#### 仪表盘 `/`

顶部一行 `<Stat>` 卡片（等宽对齐）：

```
┌─────────────┬─────────────┬─────────────┬─────────────┐
│ 总资产       │ 当日 P&L     │ 年度收益     │ vs 基准      │
│ ¥12,345,678 │ +¥45,120    │ +18.3%      │ +4.2% α     │
│             │ +0.37%      │ TWR         │ 超额         │
└─────────────┴─────────────┴─────────────┴─────────────┘
```

下方网格：

- **净值 vs 基准曲线**（占主区，约 2/3 宽）。
- **Top 5 持仓**卡片列表：名称 + 当前价 + 当日涨跌 + 占比条。
- **待复盘提醒**：到期日志列表，一键进入复盘。
- **集中度告警**：仅在超阈值时出现，警告色条。
- **本月现金流**：入金/出金/分红小计。

留白充分，卡片之间用 24px gap，无多余分割线。

#### 个股详情 `/stocks/[id]`

TradingView 式布局：

- 顶部：股票名 + 代码 + 市场徽章 + 当前价（大号 mono）+ 当日涨跌（`<PnL>`）。
- 主体：**全宽 K 线图**（含工具条、指标、买卖点 marker），占据视觉重心。
- 右侧栏（可折叠）：关键财务（PE/PB/ROE/营收 YoY）、我的持仓摘要（持股/成本/浮盈/持有天数）、AI 洞察入口。
- 下方 Tab：关联交易 / 关联日志 / 财报 / AI 洞察列表。

#### 交易录入 `/transactions/new`（强制两步 + 冷静期）

```
Step 1 — 交易信息
  股票搜索(自动补全) · 方向(买/卖分段按钮) · 数量 · 价格 · 日期 · 币种 · 账户
  右侧实时预览:预估手续费 / 成交金额 / 对持仓的影响 / 集中度变化(超阈值即时警告)

Step 2 — 决策日志(全部必填)
  决策类型 · 预期持有时间 · 目标价 · 止损价 · 退出条件
  信心评分 <ConfidenceSlider> · 当前情绪 <EmotionPicker>
  投资逻辑(≥100 字,带字数提示) · 主要风险 · 标签

提交 — <CooldownButton>
  30 秒倒计时进度环;倒计时中文案"再想想,确定就提交";可取消返回修改
  复仇交易检测命中 → 倒计时延长至 5 分钟 + 强制 AI 确认弹窗
```

提交成功后：toast "已记录" + 自动创建 30 天复盘提醒。

#### 日志详情 `/journals/[id]`

- 顶部 `<LockBadge>` 明示锁定，原始决策内容只读展示（灰底，强调"这是你当时写的"）。
- 决策快照：结构化字段卡片化排列 + 自由文本。
- **复盘时间线**：按 30/60/90 天追加的 review 列表，每条含当时价格、相对基准表现、thesis 是否成立、运气 vs 判断力、教训。
- 追加复盘入口（INSERT，不改原文）。
- AI 复盘卡片：`<AIInsightCard>`，可重新生成（受预算约束）。

#### AI 对话 `/ai/chat`

```
┌──────────┬───────────────────────────────────────┐
│ 历史会话  │  对话区(气泡:用户右/AI 左,markdown 渲染) │
│ 列表      │                                       │
│          │  ─────────────────────────────────────│
│          │  Context 选择条:勾选可被引用的数据      │
│          │  (持仓/某笔交易/某篇日志/财报)          │
│          │  输入框 + 模型徽章 + 预估成本 + 发送     │
└──────────┴───────────────────────────────────────┘
```

- 顶部显示本月 AI 预算用量进度条（接近上限变警告色）。
- 每条 AI 回复底部标注：模型、tokens、成本、是否命中缓存。
- 全局水印/脚注："AI 仅供参考，不构成投资建议，不显示买卖信号"。

#### 分析页 `/analytics/*`

- **收益分析**：TWR/IRR/年化/最大回撤/夏普/卡玛 指标卡 + 净值曲线 + 回撤水下图。
- **基准对比**：alpha/信息比率/跟踪误差/β 指标卡 + 组合 vs 基准曲线 + 滚动 alpha。
- **暴露分析**：行业/市场/币种环形图 + 明细表。
- **情绪审计**：不同情绪下的胜率/盈亏比柱状对比 + 结论文案（如"FOMO 状态下胜率仅 32%"）。

### 8.8 交互与状态规范

- **加载**：骨架屏（表格/卡片占位），不用全屏 spinner；图表用占位网格。
- **空状态**：插画 + 一句话引导 + 主操作按钮（如"还没有交易，去录入"）。
- **错误**：行内提示 + 重试按钮；同步失败在管理页可见详情。
- **乐观更新**：交易录入等用乐观 UI，失败回滚并提示。
- **危险操作**：删除/解锁用 `danger` 色二次确认弹窗，需输入或勾选确认。
- **数字动效**：数值变化用短促 count-up（≤300ms），避免眼花。
- **悬停**：表格行、图表数据点悬停联动高亮。

### 8.9 响应式

| 断点 | 适配 |
|---|---|
| 桌面 ≥1280px | 完整多栏布局，K 线全宽，侧栏展开 |
| 笔记本 1024–1280px | 侧边栏折叠为图标，仪表盘卡片 2 列 |
| 平板 768–1024px | 单列堆叠，图表全宽，右侧栏移到下方 Tab |
| 手机 <768px | 底部 Tab 导航；K 线简化（隐藏部分副图，手势缩放）；表格转卡片列表；录入流程逐屏 |

> 移动端主要用于查看与轻量复盘，录入仍走两步 + 冷静期但逐屏展示。

### 8.10 可访问性

- 颜色对比满足 WCAG AA（深色下 text-primary 对 bg-surface ≥ 4.5:1）。
- 涨跌不只靠颜色，同时带 `+/-` 号与箭头图标（色盲友好）。
- 全键盘可达，焦点环清晰；图表关键数据提供文本/表格替代。
- 完整 WCAG 合规需配合辅助技术手动测试与专家评审，非仅靠自动检查。

### 8.11 前端功能性需求清单（FE）

> 供实现与验收对照。每条对应后端 F 系列需求。

**FE-1 框架与基础**
- FE-1.1 Next.js 14 App Router + TypeScript 工程骨架。
- FE-1.2 全局 Design Tokens（CSS 变量 + Tailwind 配置），支持深/浅主题切换并持久化。
- FE-1.3 涨跌色方案切换（asia/western），组件只引用语义 token。
- FE-1.4 侧边导航 + 顶栏 + 命令面板（Cmd/Ctrl+K）+ 全局搜索（`/`）。
- FE-1.5 TanStack Query 数据层封装（统一响应壳解析、错误处理、缓存失效）。
- FE-1.6 Zustand 管理客户端状态（主题、币种、UI 偏好、冷静期计时）。

**FE-2 仪表盘**
- FE-2.1 总资产 / 当日 P&L / 年度收益 / vs 基准 四个 `<Stat>`。
- FE-2.2 净值 vs 基准曲线（区间切换）。
- FE-2.3 Top 5 持仓卡片、待复盘提醒、集中度告警、本月现金流。

**FE-3 个股详情与图表**
- FE-3.1 lightweight-charts K 线主图 + 成交量。
- FE-3.2 指标叠加（MA/EMA/布林带）与副图（MACD/RSI/KDJ）开关。
- FE-3.3 自有交易买卖点 marker + 悬停详情。
- FE-3.4 周期/复权切换、区间懒加载、全屏。
- FE-3.5 右侧财务摘要 + 我的持仓摘要 + AI 入口。

**FE-4 交易录入与导入**
- FE-4.1 两步表单（react-hook-form + zod），股票搜索自动补全。
- FE-4.2 Step 1 实时预览：手续费、成交额、持仓影响、集中度即时告警。
- FE-4.3 决策日志全字段校验（逻辑 ≥100 字）。
- FE-4.4 `<CooldownButton>` 30 秒倒计时，复仇交易延长至 5 分钟 + AI 确认。
- FE-4.5 CSV 导入：上传 → 字段映射 UI → 预览 → 批量提交，进度与失败行反馈。

**FE-5 日志与复盘**
- FE-5.1 日志列表（按股票/类型/情绪筛选）。
- FE-5.2 日志详情只读 + 锁定标识 + 复盘时间线。
- FE-5.3 追加复盘表单（INSERT 语义，不改原文）。
- FE-5.4 复盘到期提醒入口与未读计数。

**FE-6 分析**
- FE-6.1 收益分析（TWR/IRR/回撤/夏普/卡玛 + 曲线 + 水下回撤图）。
- FE-6.2 基准对比（alpha/IR/跟踪误差/β + 滚动 alpha）。
- FE-6.3 暴露分析（行业/市场/币种环形图 + 明细）。
- FE-6.4 情绪审计（情绪 × 胜率/盈亏比对比 + 结论）。

**FE-7 AI**
- FE-7.1 对话页（会话列表、Context 选择、模型/成本展示、流式输出）。
- FE-7.2 AI 洞察列表与卡片（模型徽章、成本、缓存命中、markdown）。
- FE-7.3 月度预算进度条与超限拦截提示。
- FE-7.4 全局"仅供参考"声明，无买卖信号展示。

**FE-8 其他**
- FE-8.1 关注列表（增删、标签、跳转个股）。
- FE-8.2 现金流页（账户切换、流水表、入出金）。
- FE-8.3 报表中心（月/季/年报表、失败案例库）。
- FE-8.4 设置（币种、主题、涨跌色、AI 预算、券商费率、备份）。
- FE-8.5 全局空状态、骨架屏、错误重试、危险操作二次确认。
- FE-8.6 响应式适配（桌面/笔记本/平板/手机）。

### 8.12 前端目录结构（建议）

```
frontend/
├── app/
│   ├── layout.tsx                 # 根布局(主题/字体/Query Provider)
│   ├── (dashboard)/page.tsx
│   ├── stocks/[id]/page.tsx
│   ├── transactions/
│   │   ├── page.tsx
│   │   ├── new/page.tsx
│   │   └── import/page.tsx
│   ├── journals/[id]/page.tsx
│   ├── analytics/{returns,benchmark,exposure,emotion}/page.tsx
│   ├── ai/{chat,insights}/page.tsx
│   ├── reports/page.tsx
│   ├── watchlist/page.tsx
│   └── settings/page.tsx
├── components/
│   ├── ui/                        # shadcn 定制
│   ├── charts/                    # CandleChart / EquityCurve / DonutExposure
│   ├── stats/                     # Stat / PnL / PercentBadge
│   ├── forms/                     # CooldownButton / EmotionPicker / ConfidenceSlider
│   ├── layout/                    # Sidebar / Topbar / CommandPalette
│   └── ai/                        # AIInsightCard / ChatMessage
├── lib/
│   ├── api/                       # endpoint 封装 + 类型
│   ├── hooks/                     # useHoldings / usePrices / useAIBudget ...
│   ├── format/                    # 货币/百分比/日期格式化(tabular-nums)
│   ├── theme/                     # tokens + colorScheme 逻辑
│   └── store/                     # zustand stores
└── package.json
```

---

## 9. 部署运维

### 9.1 Docker Compose

```yaml
version: '3.9'
services:
  backend:
    build: ./backend
    ports: ["8000:8000"]
    volumes:
      - ./data:/app/data
    environment:
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - BASE_CURRENCY=JPY
  frontend:
    build: ./frontend
    ports: ["3000:3000"]
    environment:
      - NEXT_PUBLIC_API_URL=http://localhost:8000
    depends_on: [backend]
```

`docker compose up -d` 启动。

### 9.2 远程访问

- **首选 Tailscale**：零配置 VPN，数据不出公网，手机可用。
- **次选 Cloudflare Tunnel**：免费 + 自定义域名 + 加密。
- **不建议**直接暴露端口到公网。

> 即便是单用户本地部署，Web 入口也应有密码登录（会话/Token），不要裸奔。

### 9.3 监控

- 后端 `/health` 接口定时 ping。
- 同步失败发 Telegram 通知。
- 关键日志输出文件，定期 grep。

### 9.4 升级路径

- SQLite → PostgreSQL：pgloader 一条命令。
- 单机 → 远程：后端 Railway，前端 Vercel。
- 预留 `user_id` 字段，需要时改多用户。

---

## 10. 实施路线图

**Phase 0：技术验证（3–5 天）**
- AKShare 拉一只 A 股日线 / yfinance 拉一只美股日线。
- Anthropic API 跑通最小财报摘要。
- 确定基准货币、金额存储方案（Decimal-as-TEXT）、技术栈最终版本。

**Phase 1：MVP（2 周）** — 目标：能记录，能查看，基础正确性。
- FastAPI 骨架 + SQLite + Alembic。
- 模型：stocks / prices / transactions / journals。
- 行情同步（单市场）。
- 交易录入（强制日志 + 冷静期）。
- 持仓自动计算 + FIFO 已实现盈亏。
- Next.js 骨架 + 设计系统 + 仪表盘 + 录入页 + 日志查看。

**Phase 2：多市场与现金流（1–2 周）**
- 港股、美股、日股；多币种 + 汇率同步。
- 现金账户 + 现金流；TWR / IRR。
- CSV 导入（至少一个券商）。

**Phase 3：基准与分析（1–2 周）**
- 基准对比、暴露分析、集中度告警。
- 技术指标 + K 线叠加买卖点（lightweight-charts）。

**Phase 4：AI 集成（1–2 周）**
- SDK 封装 + 模型分级 + 上下文组装框架。
- 三个核心 prompt + 洞察缓存 + 月度预算 + 对话页。

**Phase 5：认知偏差防御（1 周）**
- 冷静期、日志锁定中间件、持有时间警告、集中度高亮、情绪审计报表、复仇交易拦截。

**Phase 6：报表与打磨（持续）**
- 月度/季度报表、失败案例库、AI 季度模式分析、备份自动化、性能优化。

---

## 11. 风险与应对

| 风险 | 影响 | 应对 |
|---|---|---|
| 数据源 API 变更/限流 | 同步失败 | 多源容错 + 失败告警 + 手动补录 |
| 复权数据错误 | 历史成本算错 | 关键事件单独记录，定期校验 |
| 汇率缺失 | 多币种统计错 | 回退最近交易日，标记不确定 |
| **金额浮点误差** | **对账不平** | **Decimal-as-TEXT/整数最小单位，杜绝 float** |
| **拆股/公司行动算错** | **持仓数错** | **独立 corporate_actions 表 + 乘法型处理** |
| AI 成本超支 | 预算失控 | 月度硬上限 + 分级 + 缓存 |
| 项目动力衰减 | 烂尾 | MVP 优先，每 Phase 独立可用 |
| 数据丢失 | 灾难 | 每日备份 + 异地副本 + 月度全量 dump |
| 自己规避使用 | 数据闭环断 | 减少录入摩擦，初期批量导入历史 |
| 过度依赖 AI | 形成新偏差 | UI 标注"AI 仅供参考"，不显示买卖建议 |

---

## 12. 附录

### 12.1 数据源对比

| 数据源 | 覆盖 | 免费 | 实时性 | 易用性 | 适用 |
|---|---|---|---|---|---|
| AKShare | A/HK/US/期货/基金 | ✓ | 延迟 15min | ★★★★★ | 主力 |
| yfinance | US/HK/JP/全球 | ✓ | 延迟 15–20min | ★★★★ | 美/日股 |
| Tushare Pro | A 股 | 需积分 | 实时 | ★★★ | A 股深度 |
| Alpha Vantage | 全球 | 免费档限频 | 延迟 | ★★★ | 美股备份 |
| EastMoney | A/HK/US | ✓(爬) | 准实时 | ★★ | 应急 |
| Polygon.io | US 全市场 | 付费 | 实时 | ★★★★ | 升级 |

### 12.2 关键依赖版本

```toml
# backend/pyproject.toml
[project]
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.110",
    "sqlmodel>=0.0.16",
    "alembic>=1.13",
    "pandas>=2.2",
    "numpy>=1.26",
    "akshare>=1.13",
    "yfinance>=0.2",
    "pandas-ta>=0.3",
    "apscheduler>=3.10",
    "httpx>=0.27",
    "anthropic>=0.30",
    "structlog>=24.1",
    "scipy>=1.13",
    "python-dotenv>=1.0",
]
```

```json
// frontend/package.json (关键依赖)
{
  "dependencies": {
    "next": "^14",
    "react": "^18",
    "typescript": "^5",
    "tailwindcss": "^3.4",
    "@tanstack/react-query": "^5",
    "zustand": "^4",
    "lightweight-charts": "^4",
    "recharts": "^2",
    "react-hook-form": "^7",
    "zod": "^3"
  }
}
```

### 12.3 学习资源

- 《Active Portfolio Management》— Grinold & Kahn（信息比率、Alpha）
- 《The Behavior Gap》— Carl Richards（认知偏差）
- 《How to Lie with Statistics》— Darrell Huff（数据陷阱）
- pandas-ta 官方文档
- AKShare 官方文档（中文）
- Anthropic Claude API 文档
- lightweight-charts 官方文档（TradingView）

### 12.4 术语表

| 术语 | 含义 |
|---|---|
| TWR | Time-Weighted Return，时间加权收益率，排除资金进出影响 |
| IRR | Internal Rate of Return，内部收益率，实际资金回报年化 |
| Alpha | 超额收益，组合收益减基准收益 |
| 复权 | 按拆股、分红事件调整历史价格使序列连续；前复权 = 历史价向今天对齐 |
| FIFO | 先进先出，先买的先卖，用于成本计算 |
| 集中度 | 单股或单行业占组合比例 |
| 信心评分 | 决策时主观确信度，事后用于校准元认知 |
