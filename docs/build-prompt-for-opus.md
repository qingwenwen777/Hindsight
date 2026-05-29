# 建造提示词 — 个人股票分析网站（发给 Opus 4.8 的总指令）


---

## 0. 角色与总目标

你是一名资深全栈工程师，负责从零搭建一个**个人股票分析、记录与复盘平台**。

- **唯一事实来源**：`docs/stock-analyzer-design-v1.1.md`。所有数据模型、API、字段、业务规则、前端设计规范都以该文档为准。开工前先完整读一遍，之后每个阶段重读相关章节。
- **技术栈**：后端 Python 3.11 + FastAPI + SQLModel + SQLite(WAL)；前端 Next.js 14 (App Router) + TypeScript + Tailwind + shadcn/ui + TanStack Query + Zustand；K 线用 lightweight-charts。
- **项目根目录**：`e:\Project\TradeAI\`（Windows 环境，shell 为 cmd）。
- **最终交付**：一个本地可 `docker compose up` 运行、能记录交易、强制写决策日志、自动算持仓与盈亏、做基准对比、集成 AI 复盘、并带认知偏差防御的可用系统。

---

## 1. 最重要的工作纪律（务必严格遵守）

你运行在 **agent / 自动驾驶模式**：你应当自主、连续地推进，无需在每个 Step 后停下来征求许可。默认行为是"做完一步，自我验证通过，立即开始下一步"，直到整个项目达到第 5 节的"全局验收"标准。

1. **小步实现，但连续推进**。内部仍以"步骤（Step）"为最小工作单元，逐个完成；但**不要在每步后停下等待我确认**——验证通过就直接继续下一个 Step。
2. **先读后写**。修改或新建任何文件前，先确认它当前的状态（是否存在、现有内容），不要凭空假设。
3. **每步必须自我验证，且自行修复**。后端步骤要能 import / 启动 / 通过相关测试；前端步骤要能编译通过（`npm run build` 或 `tsc --noEmit`）。验证失败必须当场修复后再前进，绝不把已知报错带入下一步，也不要把错误留给我。
4. **自主决策，记录而非询问**。设计文档没覆盖的细节，按行业最佳实践自行选择并在该 Step 小结里用一句话记录理由，然后继续。**只有以下情况才暂停并明确询问我**：(a) 会破坏数据正确性或改变整体架构方向的分歧；(b) 需要我提供的外部凭据/密钥（如 Anthropic API Key）且缺失会阻断后续；(c) 出现需要删库、重写大量已完成代码等高风险且不可逆的操作。除此之外一律自行决定、继续前进。
5. **被外部因素阻断时不要空转**。若某 Step 因缺少凭据或网络受限无法完成（如无 API key、数据源不可达），实现优雅降级 / mock，标注 TODO，**跳过该处并继续后续可做的 Step**，最后统一汇总待我处理的事项，不要卡死在一处反复重试。
6. **金额绝不用浮点**。所有金额/价格/数量在 DB 用 TEXT 存、Python 侧用 `Decimal` 运算（见文档第 4 章 v1.1 修正）。任何地方出现 `float` 参与金额计算都算 bug。
7. **不要伪造数据正确性**。盈亏、TWR、IRR、复权、拆股这些计算必须有对应单元测试覆盖，并给出一个手算可验证的样例。
8. **自动提交 git**。每完成一个 Step 自动用清晰的 message 提交一次（`feat(scope): ...`）。除非我另有要求，提交即可，无需等待确认。
9. **不写买卖信号 / 不预测股价**。AI 模块只做定性分析，所有 AI 输出处必须带"仅供参考"声明。

---

## 2. 全局技术约定

**通用**
- 所有代码、注释、文档用中文注释 + 英文标识符。
- 命名：Python `snake_case`，TS `camelCase`，组件 `PascalCase`，DB 表/列 `snake_case`。
- 时间统一存 UTC，展示按 JST（Asia/Tokyo）。日期字段用 ISO 8601。
- 错误处理显式化，不吞异常；同步/外部 API 调用必须有重试与超时。

**后端**
- 目录结构严格按文档 3.3 节。
- 用 `pydantic-settings` 管理配置，敏感值走 `.env`（提供 `.env.example`）。
- 统一响应壳：`{ code, message, data, meta }`（见文档第 6 章）。
- 用 `structlog` 输出结构化日志。
- 测试用 `pytest`，放 `backend/tests/`，关键计算（pnl/returns/fees/adjust/concentration）必须有测试。
- Decimal 适配：在 `core/money.py` 实现金额类型与 SQLModel 的 TEXT↔Decimal 转换。

**前端**
- 严格按文档第 8 章设计规范：深色默认主题、TradingView 风格、Design Tokens 用 CSS 变量 + Tailwind theme 扩展。
- 涨跌色用语义 token（`up`/`down`），支持 asia/western 切换，组件内禁止硬编码红绿。
- 数字一律 `tabular-nums` 等宽对齐，金额/百分比走统一 `lib/format` 格式化函数。
- 数据请求统一走 `lib/api` 封装 + TanStack Query；客户端状态用 Zustand。
- 组件优先复用 shadcn/ui，项目特有复合组件按文档 8.5 节实现。

**环境约定（Windows / cmd）**
- 命令分隔用 `&`，不要用 `&&`。
- 不要在前台启动长时间运行的进程（dev server、watch）。需要时告诉我手动运行，并给出确切命令。
- 包管理：后端用 `uv` 或 `pip` + `pyproject.toml`；前端用 `npm`。

---

## 3. 每个 Step 的固定输出格式

每完成一个 Step，按下面格式简要汇报，**然后立即继续下一个 Step**（不要停下等待）：

```
### ✅ Step X.Y 完成：<标题>

**做了什么**
- （要点，3-6 条）

**新增/修改文件**
- path/to/file —（一句话说明）

**如何验证 / 验证结果**
- 我运行了 <命令>，结果 <通过/输出摘要>

**我做的自主决定**（如有）
- <决定> ——理由：<一句话>

**已提交**
- feat(scope): ...

**下一步**
- 继续 Step X.(Y+1)：<标题>
```

> 仅当触发第 1.4 节中"需要暂停询问"的三种情况时，才在汇报末尾改为明确向我提问并暂停；否则一律连续推进。

---

## 4. 分阶段任务清单

> 阶段对应设计文档第 10 章路线图。每个 Step 都要满足其"验收标准"才算完成。

### Phase 0 — 项目初始化与技术验证

**Step 0.1 — 仓库骨架**
- 创建目录结构：`backend/`、`frontend/`、`data/`（含 `backups/`、`exports/`）、`docs/`（已存在）。
- 根目录加 `.gitignore`（Python、Node、SQLite、.env、data 产物）、`README.md`（项目简介 + 启动说明占位）、`docker-compose.yml`（按文档 9.1，可先占位）。
- 验收：目录树与文档 3.3 一致；`git status` 干净可初始化。

**Step 0.2 — 后端工程骨架**
- `backend/pyproject.toml`（依赖按文档 12.2）、`app/main.py`（FastAPI 实例 + `/health` 接口返回 `{code:0,...}`）、`app/config.py`（pydantic-settings）、`app/database.py`（SQLModel engine + WAL pragma）。
- 提供 `.env.example`。
- 验收：能启动并访问 `/health` 返回 200（你用一次性命令验证，不要常驻 server）；`pytest` 能跑（哪怕 0 用例）。

**Step 0.3 — 前端工程骨架 + 设计系统**
- 初始化 Next.js 14 (App Router) + TS + Tailwind + shadcn/ui。
- 落地设计 Tokens（文档 8.2）：在 Tailwind/CSS 变量里配置深色主题配色、字体、字号阶梯；实现主题切换与 colorScheme(asia/western) 的基础设施（先做 store + Provider，UI 后续接）。
- 实现根布局（Topbar + Sidebar 占位）。
- 验收：`npm run build` 通过；首页能渲染出深色主题外壳。

**Step 0.4 — 数据源 / AI 连通性验证（spike）**
- 写一个一次性脚本 `backend/scripts/spike.py`：用 AKShare 拉一只 A 股日线、yfinance 拉一只美股日线、调用 Anthropic 跑一个最小财报摘要（无 key 时优雅跳过并提示）。
- 验收：脚本能跑通至少行情部分并打印前几行；把可能的环境坑（如 AKShare 依赖）记到 README。

---

### Phase 1 — MVP（能记录、能查看、基础正确）

**Step 1.1 — 核心数据模型**
- 按文档第 4 章实现 SQLModel 模型：`stocks`、`prices`、`transactions`、`journals`（先这四个 + 基础）。严格落实 Decimal-as-TEXT。
- 配置 Alembic，生成首个迁移。
- 验收：迁移能 upgrade 出库；用一个测试插入/读回一条带 Decimal 的记录，值精确无误差。

**Step 1.2 — 金额与货币基础设施**
- `core/money.py`（Money/Decimal 类型 + 转换）、`core/fees.py`（手续费引擎 + 预置规则，文档 7.3）、`core/currency.py`（占位，Phase 2 接汇率）。
- 验收：手续费引擎对 A 股买/卖、美股卖各有一个手算样例的单元测试。

**Step 1.3 — 行情同步（单市场 A 股）**
- `services/data_sync/akshare_client.py` + 增量同步逻辑 + 数据校验（high>=low 等，文档 5.1）。
- 提供 `POST /admin/sync/prices?market=CN` 触发。
- 验收：能把一只股票的日线写进 `prices`，重复同步不产生重复行（UPSERT）。

**Step 1.4 — 交易录入 API（强制日志）**
- `POST /transactions`：在一个事务里写 `journals(is_locked=true)` + `transactions(关联 journal_id)`，并失效持仓缓存。缺日志必填字段则 422。
- 日志锁定中间件：拦截对已锁定 journal 的 UPDATE。
- 验收：测试覆盖"无日志被拒""提交后 journal 锁定不可改"。

**Step 1.5 — 持仓与 FIFO 盈亏**
- `services/analysis/pnl.py`：按文档 4.3/5.4 用 Python 从 transactions(+后续的 corporate_actions 接口预留) 计算持仓与 FIFO 已实现盈亏、浮动盈亏。
- API：`GET /portfolio/holdings`、`GET /portfolio/summary`。
- 验收：构造"买100→买100→卖150"样例，FIFO 已实现盈亏手算可对上，有单元测试。

**Step 1.6 — 前端：仪表盘 + 录入页 + 日志查看（接真实 API）**
- `lib/api` 封装 + TanStack Query hooks。
- 仪表盘 `<Stat>` 卡片 + Top 持仓（文档 8.7）。
- 交易录入两步表单 + `<CooldownButton>` 30 秒冷静期（文档 8.7）。
- 日志列表 + 详情（只读 + 锁定标识）。
- 验收：`npm run build` 通过；本地能完成"录入一笔交易并在仪表盘看到持仓"的闭环（你用脚本或说明验证后端，前端确认编译与组件渲染）。

---

### Phase 2 — 多市场与现金流

**Step 2.1 — 多市场行情 + 容错优先级**
- 增加 yfinance 客户端，按文档 5.1 容错链路（美/港/日）。多市场调度（APScheduler，时间表见 5.1，本地可手动触发）。
- 验收：美股、港股各能同步一只；失败时按优先级回退并记录同步日志。

**Step 2.2 — 汇率 + 多币种**
- `fx_rates` 模型 + 同步（USDJPY=X 等）+ `core/currency.py` 完成换算（缺失回退最近交易日并标记估算）。
- 组合汇总支持 `currency=JPY|USD|CNY`。
- 验收：跨币种持仓能按基准币种正确汇总，有测试。

**Step 2.3 — 现金账户与现金流**
- `cash_accounts` / `cash_flows` 模型 + API（入金/出金/分红/利息）；交易自动产生对应 cash_flow。
- 验收：录入交易后现金账户余额变动正确。

**Step 2.4 — TWR / IRR**
- `services/analysis/returns.py`：TWR（现金流切段几何相乘）、IRR（scipy.brentq）。
- API：`GET /portfolio/returns?type=TWR|IRR`。
- 验收：构造已知答案的现金流序列，TWR/IRR 数值对得上，有测试。

**Step 2.5 — 公司行动（拆股/送股/配股）**
- `corporate_actions` 模型 + 持仓计算里的乘法型处理（文档 4.3）。
- 验收："持股100→1拆2"后持股变 200、单股成本减半，有测试。

**Step 2.6 — CSV 导入（至少一个券商）**
- `POST /transactions/import`：上传→检测→字段映射→预览→批量写入，导入项创建占位 journal(`is_imported=true`)。前端做映射 UI。
- 验收：用一个样例 CSV 完成导入闭环。

---

### Phase 3 — 基准与分析

**Step 3.1 — 技术指标**
- `services/analysis/indicators.py`：MA/EMA/MACD/RSI/布林带/KDJ（pandas-ta）。API `GET /stocks/{id}/indicators`。
- 验收：对一段已知数据，指标首尾值与参考实现一致，有测试。

**Step 3.2 — 基准对比**
- `services/analysis/benchmark.py`：alpha/信息比率/跟踪误差/β（每市场默认基准见 5.4）。API `GET /portfolio/benchmark-comparison`。
- 验收：构造样例验证 alpha 计算，有测试。

**Step 3.3 — 暴露与集中度**
- `services/biases/concentration.py`：行业/市场/币种暴露 + 集中度（单股>20%/单行业>40% 阈值）。API `GET /portfolio/exposure`、`/concentration`。
- 验收：超阈值能被正确标记。

**Step 3.4 — 前端：个股详情 K 线（lightweight-charts）**
- `<CandleChart>`：主图 K 线 + 成交量，叠加 MA/布林带，副图 MACD/RSI；自有交易买卖点 marker；周期/复权切换、区间懒加载（文档 8.6）。
- `<EquityCurve>` 净值 vs 基准；`<DonutExposure>` 暴露环形图。
- 验收：`npm run build` 通过；K 线能渲染并叠加指标与买卖点。

---

### Phase 4 — AI 集成

**Step 4.1 — AI 客户端 + 模型分级 + 预算**
- `services/ai/client.py`（anthropic SDK 封装）、`budget.py`（月度硬上限，文档 5.5，默认 2000 JPY）、模型分级表。
- `ai_insights` 模型 + 缓存（input_hash，7 天命中）。
- 验收：无 key 时优雅降级；预算超限拦截有测试（mock）。

**Step 4.2 — 上下文组装 + 三个核心 Prompt**
- `context_builder.py`（数字由代码算）+ `prompts.py`（交易复盘 / 魔鬼代言人 / 失败模式识别，文档 5.5 原文模板）。
- API：`POST /ai/analyze`、`GET /ai/insights`。
- 验收：能对一笔真实交易生成复盘并写入缓存；重复请求命中缓存不再扣费。

**Step 4.3 — AI 对话页**
- `POST /ai/chat` + 前端对话页（会话列表、Context 选择、模型/成本展示、预算进度条、流式输出、"仅供参考"声明，文档 8.7）。
- 验收：能基于选中的持仓/日志上下文对话；`npm run build` 通过。

---

### Phase 5 — 认知偏差防御

**Step 5.1 — 防御规则后端**
- `services/biases/`：持有时间警告、复仇交易检测（连亏3次后买同股→冷静期5分钟+AI确认）、情绪审计统计（不同情绪胜率）。
- 验收：每条规则有触发/不触发的测试。

**Step 5.2 — 防御交互前端**
- 录入流程接入：集中度即时告警、持有时间警告弹窗、复仇交易延长冷静期、`<ConcentrationAlert>`。
- 验收：构造场景能在 UI 触发对应告警。

**Step 5.3 — 情绪审计页**
- `/analytics/emotion`：情绪×胜率/盈亏比对比 + 结论文案。API `GET /reports/emotion-audit`。
- 验收：能展示按情绪分组的胜率。

---

### Phase 6 — 报表与打磨

**Step 6.1 — 报表中心**
- 月/季/年报表 API + 页面；失败案例库（亏损>5% 交易聚合）。
- 验收：能生成某月报表。

**Step 6.2 — AI 季度模式分析**
- 季度任务调用失败模式识别 Prompt，输出模式 + 支持交易 id + 改进建议。
- 验收：能对历史亏损交易生成季度模式报告。

**Step 6.3 — 备份与运维收尾**
- 每日备份脚本（文档 7.5）、`/health` 监控、docker-compose 完整可用、README 完善启动文档。
- 验收：`docker compose up -d` 后前后端可访问；备份脚本能产出加密/压缩文件。

**Step 6.4 — 性能与全局打磨**
- 行情 parquet 缓存、持仓增量缓存、前端骨架屏/空状态/错误重试/响应式自查（文档 8.8/8.9）。
- 验收：仪表盘 < 2s、持仓查询 < 500ms 的目标做一次实测说明。

---

## 5. 全局验收（项目完成的定义）

- `docker compose up -d` 一键启动，前端可登录访问。
- 能完成闭环：录入交易（强制日志+冷静期）→ 自动算持仓/FIFO 盈亏 → 基准对比 → AI 复盘 → 到期复盘提醒。
- 关键计算（pnl/returns/fees/adjust/concentration/benchmark）均有通过的单元测试。
- 金额全链路 Decimal，无浮点误差。
- AI 模块有预算上限、缓存、"仅供参考"声明，且不输出买卖信号。
- README 含完整本地启动与远程访问（Tailscale）说明。

---

## 6. 现在开始

1. 先用不超过 5 行简述你对项目的理解，确认你已读完本提示词与 `docs/stock-analyzer-design-v1.1.md`。**这一步无需我确认，简述完直接开工。**
2. 然后从 Step 0.1 开始，**连续、自主地**按顺序执行每个 Step，每步按第 3 节格式简报后立即进入下一步，直到达成第 5 节的全局验收，或遇到第 1.4 节规定的必须暂停询问的情况。
3. 不要为了等待我的指令而停下；只在真正被阻断（缺凭据/高风险/架构分歧）时才向我提问。
