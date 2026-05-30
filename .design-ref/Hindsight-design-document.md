# Hindsight 产品与设计文档

> 面向个人长期投资学习与复盘的股票分析工具。Hindsight 的核心不是交易执行,而是把"市场怎么走"和"我当时怎么想"放进同一个系统里,让每一笔投资决策都能被记录、检验和改进。

**版本**: v1.0  
**日期**: 2026-05-10  
**项目名**: Hindsight  
**目标用户**: 仅本人使用,非 SaaS 产品

---

## 1. 产品定位

### 1.1 一句话定位

Hindsight 是一个用于长期投资学习与复盘的个人工具,通过结构化交易日志、组合分析、AI 投资教练和认知偏差防御机制,帮助用户把投资从"凭感觉"变成"可复盘、可学习、可改进"的过程。

### 1.2 核心价值

1. **结构化记录每一笔交易决策**  
   记录买卖原因、信心、情绪、目标价、止损价、退出条件和预期持有周期。

2. **把 AI 用作投资教练,而不是买卖信号机器**  
   AI 负责复盘、质疑、模式识别和月度总结,不直接预测股价,不输出下单建议。

3. **用产品设计对抗认知偏差**  
   冷静期、日志锁定、集中度告警、复盘提醒和情绪审计都属于产品内置的纪律系统。

4. **把市场走势和当时想法连接起来**  
   K 线图与决策日志联动是 Hindsight 的根本差异点:不是只看价格,而是看价格背后的自己。

### 1.3 明确不做

- 不做实时高频交易工具
- 不做券商下单
- 不做社交、社区或多人协作
- 不做股价预测
- 不做 SaaS 商业化
- 不把界面做成券商 App 式信息过载

---

## 2. 产品原则

### 2.1 冷静

Hindsight 的界面应降低冲动交易欲望。涨跌信息必须清楚,但不制造实时闪烁、强刺激和 FOMO。

### 2.2 专业

视觉参考 TradingView、GitHub Dark、Linear。页面需要有金融工具的精密感,但不模仿交易终端的信息拥挤。

### 2.3 诚实

产品要如实展示跑赢/跑输、集中度、错误决策、未完成复盘和 AI 发现的问题。尤其 Alpha 卡片不能美化结果。

### 2.4 克制

只在必要处使用颜色。涨跌色只用于数字;红色只代表下跌或危险;蓝色只作为全局唯一行动强调色。

---

## 3. 信息架构

### 3.1 主导航

Hindsight 的一级导航:

- 仪表盘
- 持仓
- 交易
- 日志
- 分析
- AI
- 设置

### 3.2 推荐路由

```text
/                         仪表盘
/portfolio                组合总览
/portfolio/holdings       持仓详情
/transactions             交易列表
/transactions/new         录入交易
/transactions/import      批量导入
/journals                 决策日志
/journals/[id]            日志详情与复盘
/analytics/returns        收益分析
/analytics/benchmark      基准对比
/analytics/exposure       暴露分析
/analytics/emotion        情绪审计
/ai/chat                  AI 对话
/ai/insights              AI 洞察
/reports                  报表中心
/watchlist                关注列表
/settings                 设置
```

---

## 4. 视觉系统

当前已有三个 HTML 原型:

- `design-system.html`: 视觉系统
- `dashboard.html`: 仪表盘页面
- `decision-chart.html`: K 线图 + 决策日志联动组件

### 4.1 主题策略

Hindsight 支持深色与浅色系统:

- **深色主题**:适合长期使用、夜间复盘、金融终端感
- **浅色主题**:参考 TradingView Market Summary,强调白底、留白、极细边框和清晰图表
- **打印模式**:自动使用浅色

主题通过 CSS 变量控制:

```html
<html data-theme="light">
<html data-theme="dark">
```

### 4.2 深色主题 Token

```css
--bg-canvas: #131722;
--bg-surface: #1e222d;
--bg-elevated: #2a2e39;

--border-subtle: #2a2e39;
--border-default: #363a45;
--border-strong: #4a4f5a;

--text-primary: #f0f3fa;
--text-secondary: #d1d4dc;
--text-tertiary: #787b86;

--accent: #2962ff;
--accent-hover: #1e53e5;

--market-up: #26a69a;
--market-down: #ef5350;
--market-flat: #787b86;
```

### 4.3 浅色主题 Token

```css
--bg-canvas: #ffffff;
--bg-surface: #ffffff;
--bg-elevated: #f0f3fa;

--border-subtle: #f0f3fa;
--border-default: #e0e3eb;
--border-strong: #c7ccd8;

--text-primary: #131722;
--text-secondary: #2a2e39;
--text-tertiary: #787b86;

--accent: #2962ff;
--accent-hover: #1e53e5;

--market-up: #00897b;
--market-down: #d8433e;
--market-flat: #787b86;
```

### 4.4 字体

```css
--font-sans: Inter, "SF Pro Text", "Segoe UI", system-ui, sans-serif;
--font-mono: "SFMono-Regular", "Roboto Mono", "Cascadia Mono", "Segoe UI Mono", Consolas, ui-monospace, monospace;
```

数字必须使用等宽字体:

```css
.num {
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums lining-nums;
  font-feature-settings: "tnum" 1, "lnum" 1;
}
```

### 4.5 字号与字重

只使用两档字重:

- `400`:正文
- `500`:标题、按钮、关键数字

字号原则:

- KPI 大数字: `36px / 500 / mono`
- 页面主标题: `24px / 500`
- 中型标题: `14px / 500`
- 正文: `14px`
- 元信息: `13px`
- 表格表头: `11px / uppercase / letter-spacing 0.08em`
- Badge: `10px`

### 4.6 颜色使用规则

1. 涨跌色仅用于数字或图表线条。
2. 红色只代表下跌或危险。
3. Primary Button 是全站唯一蓝色按钮。
4. 链接、装饰和普通按钮不使用涨跌色。
5. 警告面板可用左侧 2px 语义色边框,但主体保持克制。

### 4.7 圆角、边框、阴影

深色系统:

- 卡片边框: `1px solid --border-default`
- 卡片圆角: `6px` 到 `16px`,金融页偏向 TradingView 的柔和卡片时使用 `16px`
- 深色卡片高光:

```css
box-shadow: inset 0 1px 0 rgba(255,255,255,0.04);
```

浅色系统:

- 卡片边框: `1px solid --border-default`
- 大卡片圆角: `16px`
- 搜索框圆角: `999px`
- 不使用 Material Design elevation 阴影

---

## 5. 页面设计:仪表盘

对应文件:`dashboard.html`

### 5.1 页面目标

一屏内回答四个问题:

1. 我现在多有钱?
2. 跑赢市场了吗?
3. 有什么需要注意?
4. 持仓里谁是主角,谁拖后腿?

### 5.2 页面结构

```text
Topbar 60px
├── Logo: Hindsight
├── 全局搜索
├── 基准货币切换
└── 设置

Sidebar 220px
├── 仪表盘
├── 持仓
├── 交易
├── 日志
├── 分析
├── AI
└── 设置

Main 最大 1280px
├── 第一行: 4 个 KPI 卡片
├── 第二行: 净值曲线图 + 告警面板
└── 第三行: Top 5 持仓表格
```

### 5.3 KPI 卡片

四个卡片:

| 卡片 | 数据 | 设计重点 |
|------|------|----------|
| Total Assets | `12,847,320 JPY` | 回答"我现在多有钱" |
| YTD Return | `+8.42%` | 显示绝对收益 |
| Alpha (YTD) | `−4.38%` | 产品灵魂,必须诚实显示跑输 |
| Cash | `2,140,000 JPY` | 现金比例与行动空间 |

Alpha 卡片规则:

- 跑赢基准:绿色数字
- 跑输基准:红色数字
- 不用中性文案弱化结果

### 5.4 净值曲线

曲线规则:

- 组合:绿色
- 基准 Nikkei 225:蓝色
- 组合曲线底部可用轻渐变填充
- 渐变只用于图表数据区域,不用于 UI 装饰

### 5.5 告警面板

告警项:

- `7203.T at 28% of book`
- `3 trades pending review`
- `AI: monthly report ready`

视觉规则:

- 每条告警左侧 `2px` 语义色边框
- 红色:集中度
- 黄色:待复盘
- 蓝色:AI
- 主体背景保持白色或炭色,不大面积染色

### 5.6 Top 5 持仓表格

表格字段:

- Code + Name
- Price
- Cost
- P/L
- Weight
- Status

表格规则:

- 代码列白色/主文本色,字重 500
- 名称 `11px` 灰色
- 数字列右对齐
- 所有价格、成本、收益率、权重使用等宽字体

---

## 6. 核心特性组件:K 线图 + 决策日志联动

对应文件:`decision-chart.html`

### 6.1 组件定位

这是 Hindsight 最关键的产品差异点。

TradingView 展示"市场怎么走";Hindsight 必须同时展示:

- 市场怎么走
- 我在当时怎么想
- 我的决策后来对不对
- 当时的情绪和信心是否可靠

### 6.2 组件结构

```text
股票头部
├── 代码: 7203.T
├── 名称: Toyota Motor
├── 当前价: 3,142
└── 涨跌: +38 (+1.22%)

快速指标条
├── 成本: 2,580
├── 股数: 1,200
├── 市值: 3,770,400
├── 浮盈: +674,400
└── 持有: 142 天

主图区 450px
├── SVG 蜡烛图
├── 买入标记: 绿色 ▲B
├── 卖出标记: 红色 ▼S
├── 目标价虚线: 黄色 3,300
├── 止损价虚线: 红色 2,400
└── 时间范围: 1M / 3M / 6M / 1Y / All

决策日志横向滚动
├── BUY 2025-12-18
├── BUY 2026-02-10
└── SELL 2026-04-22

AI Coach Review
└── 默认收起
```

### 6.3 数据

交易记录:

| 日期 | 类型 | 价格 | 股数 | 主张 | 信心 | 情绪 |
|------|------|------|------|------|------|------|
| 2025-12-18 | BUY | 2,580 | 400 | PE 9.2x 远低于 5 年均值 13x | 4 stars | Calm |
| 2026-02-10 | BUY | 2,720 | 800 | Q4 财报营收超预期,加仓 | 5 stars | Calm |
| 2026-04-22 | SELL | 3,180 | 200 | 接近目标价,获利了结部分 | 3 stars | Hesitant |

水平线:

- 目标价:`3,300`
- 止损价:`2,400`

### 6.4 联动行为

当前原型只用注释说明,不实现 JS。

目标交互:

```text
点击 K 线上的 ▲B 标记
→ 对应日志卡片高亮
→ 日志横向滚动到视野内

点击日志卡片
→ 对应 K 线买卖点位置画一个圆环动画
```

### 6.5 设计要求

- 图表必须优先服务复盘,不是炫技。
- 买卖点必须清楚,但不能遮挡 K 线。
- 日志卡片要能快速看出:当时买卖理由、信心、情绪、当前盈亏、Alpha。
- AI Review 默认收起,避免抢走用户自己的判断。

---

## 7. 功能需求

### 7.1 数据同步

- 多市场行情:A 股、港股、美股、日股
- 每日同步关注列表和持仓股日线 OHLCV
- 默认前复权
- 同步财报核心指标、估值数据和汇率
- 失败重试与告警

推荐同步时间(JST):

| 数据 | 时间 |
|------|------|
| 日股日线 | 每交易日 16:00 |
| A 股日线 | 每交易日 16:30 |
| 港股日线 | 每交易日 17:30 |
| 美股日线 | 次日 06:30 |
| 汇率 | 每日 09:00 |
| 财报指标 | 每周六 10:00 |

### 7.2 交易与持仓

- 手动录入买入/卖出
- 支持分红、拆股、配股
- 自动计算手续费
- 支持券商 CSV 导入
- 持仓从交易流水推导,避免手动维护
- 支持 FIFO 或加权平均成本
- 多币种统一展示

### 7.3 投资日志

每笔交易必须绑定日志:

- 决策类型
- 预期持有时间
- 目标价
- 止损价
- 退出条件
- 信心评分
- 决策时情绪
- 主要逻辑
- 风险

日志提交后锁定,只能追加复盘。

### 7.4 分析

- 总收益
- 年化收益
- TWR
- IRR
- 最大回撤
- 夏普
- 基准对比
- Alpha
- 行业/市场/币种暴露
- 集中度
- 胜率、盈亏比、持有时间分布

### 7.5 AI Coach

AI 的任务:

- 单笔交易复盘
- 魔鬼代言人
- 财报摘要
- 同行对比
- 失败模式识别
- 月度报告
- 自由问答

AI 的边界:

- 不预测股价
- 不直接给买卖建议
- 引用数字必须来自系统上下文
- 输出应短、直接、可验证

### 7.6 认知偏差防御

| 机制 | 触发 | 行为 |
|------|------|------|
| 冷静期 | 提交交易前 | 30 秒倒计时 |
| 日志锁定 | 提交日志后 | 不可修改,只能追加复盘 |
| 集中度告警 | 单股 > 20% | 红色风险提示 |
| 持有时间警告 | 长期决策短期卖出 | 要求说明为什么改变主意 |
| 情绪审计 | 月度复盘 | 统计不同情绪下的胜率 |
| 待复盘提醒 | 30/60/90 天 | 提醒追加 review |

---

## 8. 技术架构

### 8.1 总体架构

```text
数据源层
AKShare / yfinance / Alpha Vantage / 财经新闻
        ↓
后端服务层
FastAPI / pandas / APScheduler / AI Service
        ↓
数据存储层
SQLite WAL / 文件缓存 / 备份
        ↓
前端层
Next.js / TypeScript / Tailwind / 图表
```

### 8.2 技术栈

后端:

- Python 3.11+
- FastAPI
- SQLModel
- pandas + numpy
- AKShare + yfinance
- APScheduler
- anthropic SDK
- structlog
- pytest

前端:

- Next.js 14 App Router
- TypeScript
- Tailwind
- shadcn/ui 可选
- TanStack Query
- Zustand
- ECharts 用于正式 K 线
- Recharts 或 SVG 用于轻量图

存储:

- 起步:SQLite WAL
- 后续:PostgreSQL
- 缓存:进程内 LRU + 文件缓存

---

## 9. 数据模型

### 9.1 核心实体

```text
stocks ─1:N→ prices
stocks ─1:N→ transactions ─1:1→ journals ─1:N→ reviews
cash_accounts ─1:N→ cash_flows
transactions ─N:1→ cash_flows
ai_insights → stocks / transactions / journals / portfolio
```

### 9.2 表设计摘要

| 表 | 用途 |
|----|------|
| stocks | 股票元信息 |
| prices | 日线行情 |
| transactions | 交易流水 |
| journals | 决策日志 |
| reviews | 事后复盘 |
| cash_accounts | 现金账户 |
| cash_flows | 现金流 |
| fx_rates | 汇率 |
| fee_rules | 手续费规则 |
| watchlist | 关注列表 |
| ai_insights | AI 分析缓存 |

### 9.3 关键原则

持仓不单独建表,从 `transactions` 推导,避免交易记录和持仓表不一致。

---

## 10. API 设计

统一前缀:

```text
/api/v1
```

股票:

```text
GET /stocks/search
GET /stocks/{id}
GET /stocks/{id}/prices
GET /stocks/{id}/indicators
GET /stocks/{id}/financials
```

交易:

```text
POST /transactions
GET /transactions
GET /transactions/{id}
POST /transactions/import
```

日志:

```text
POST /journals
GET /journals
GET /journals/{id}
POST /journals/{id}/reviews
```

组合:

```text
GET /portfolio/holdings
GET /portfolio/summary
GET /portfolio/returns
GET /portfolio/benchmark-comparison
GET /portfolio/exposure
GET /portfolio/concentration
```

AI:

```text
POST /ai/analyze
GET /ai/insights
POST /ai/chat
GET /ai/budget
```

---

## 11. 部署与资源估算

### 11.1 资源占用

FastAPI 后端:

- 稳态:300-500 MB
- 峰值:600-800 MB

Next.js 前端:

- 稳态:200-350 MB

SQLite:

- 常驻进程:无
- 数据文件:约 500 MB - 1.5 GB

系统 + Docker:

- Linux:150-300 MB
- Docker daemon:50-100 MB

### 11.2 配置建议

| 档位 | 配置 | 结论 |
|------|------|------|
| 最低能跑 | 1 vCPU / 1 GB RAM / 20 GB SSD | 可验证,长期偏紧 |
| 推荐底线 | 1 vCPU / 2 GB RAM / 25-40 GB SSD | 个人使用够用 |
| 舒适甜点 | 2 vCPU / 4 GB RAM / 40 GB SSD | 推荐上云配置 |
| 过度 | 4 vCPU / 8 GB RAM+ | 暂无必要 |

实际建议:

1. 先在本机或 Mac mini 跑。
2. 用 Tailscale 做远程访问。
3. 确认使用习惯后再上云。
4. 真要上云,优先 `2C / 4GB`。

---

## 12. 实施路线图

### Phase 0:技术验证

- 拉取一只 A 股日线
- 拉取一只美股日线
- 跑通 Anthropic API
- 确认 SQLite + FastAPI + Next.js 基础链路

### Phase 1:MVP

- FastAPI 骨架
- SQLite + Alembic
- stocks / prices / transactions / journals
- 行情同步
- 交易录入
- 强制日志
- 持仓计算
- 仪表盘

### Phase 2:多市场与现金流

- 港股、美股、日股
- 多币种汇率
- 现金账户
- TWR / IRR
- CSV 导入

### Phase 3:分析与可视化

- 基准对比
- Alpha
- 集中度告警
- K 线买卖点
- 持仓详情页

### Phase 4:AI Coach

- AI SDK 封装
- 上下文构建
- 交易复盘
- 魔鬼代言人
- 月度报告
- AI 预算

### Phase 5:认知偏差防御

- 冷静期
- 日志锁定
- 复盘提醒
- 情绪审计
- 失败案例库

---

## 13. 当前原型文件

| 文件 | 说明 |
|------|------|
| `design-system.html` | Hindsight 视觉系统 |
| `dashboard.html` | 仪表盘页面,浅色主题 |
| `dashboard-dark.html` | 仪表盘页面,暗色主题 |
| `decision-chart.html` | K 线图 + 决策日志联动组件,浅色主题 |
| `decision-chart-dark.html` | K 线图 + 决策日志联动组件,暗色主题 |

本地预览:

```text
http://127.0.0.1:4173/design-system.html
http://127.0.0.1:4173/dashboard.html
http://127.0.0.1:4173/dashboard-dark.html
http://127.0.0.1:4173/decision-chart.html
http://127.0.0.1:4173/decision-chart-dark.html
```

---

## 14. 风险与约束

| 风险 | 应对 |
|------|------|
| 数据源不稳定 | 多源容错 + 手动补录 |
| pandas 内存爆 | 不整表载入 prices,按需查询 |
| AI 成本失控 | 模型分级 + 缓存 + 月度预算 |
| 自己不愿记录 | 降低录入摩擦,但保留强制日志 |
| 数据丢失 | 每日 SQLite backup + 异地加密备份 |
| 过度依赖 AI | AI 只做 coach,不做买卖建议 |

---

## 15. 设计判断备忘

Hindsight 的核心竞争力不是行情数据,也不是图表库,而是"决策上下文"。

因此产品优先级应是:

1. 交易记录准确
2. 决策日志不可丢失
3. K 线与日志联动清晰
4. Alpha 和基准对比诚实
5. AI 能发现用户反复出现的错误模式

视觉上,Hindsight 应该像一台冷静的复盘仪器,而不是刺激用户交易的行情终端。
