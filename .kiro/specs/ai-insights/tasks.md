# Implementation Plan

## Overview

本计划将"AI 洞察中心"分解为 17 个增量任务，遵循设计中的实施顺序：先后端模型与纯计算引擎（可独立测试），再服务层与 API，接着调度与股票池，最后前端页面与导航，收尾统一验证、提交、部署。每个任务标注其覆盖的需求编号。

## Tasks

- [x] 1. 数据模型与迁移
  - 新建 `backend/app/models/insight.py`：`InsightDocument`、`ReportConfig`、`ScreenerRule`、`PriceAlert`（DecimalString / JSON 列 / utcnow，唯一约束见设计）
  - 在 `backend/app/models/__init__.py` 集中导入注册 metadata
  - 新增 Alembic 迁移建 4 张表（参考既有 version 写法）
  - _Requirements: 7.1, 7.2, 7.3, 11.1_

- [x] 2. 规则筛选引擎（纯计算，可测）
  - 新建 `backend/app/services/screener/engine.py`：`run_screen(session, conditions, markets)` + `ScreenHit`
  - 字段解析（PE/PB/ROE/营收增速/净利增速/股息率/市场/行业/in_watchlist/in_holdings）、运算符（<,<=,>,>=,=,between）、AND 组合、缺字段→missing、百分比换算
  - 不调用任何 AI/网络
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.7_

- [x] 3. 日报上下文与提示
  - 新建 `backend/app/services/insights/context.py`：`build_report_context`（市场概览复用 `DEFAULT_BENCHMARKS`、异动阈值、触价、决策日志对照、待办=reminders+集中度），数字全部代码算
  - 在 `backend/app/services/ai/prompts.py` 增加 `DAILY_REPORT`、`SCREENER_REVIEW` 模板与 render 函数（注入 focus/constraints/tone/detail/language，红线沿用 SYSTEM_BASE）
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 3.2, 3.3_

- [x] 4. 日报服务（生成 + 降级 + 幂等）
  - 新建 `backend/app/services/insights/daily_report.py`：`build_daily_report(session, market, config)`，调用 `ai_client.analyze`；无 Key/超预算→机械 Markdown + degraded
  - 机械 Markdown 渲染器 `render_mechanical_md` 与合成器 `compose_md`
  - 按 (doc_type, market, report_date) UPSERT 幂等；记录 model/token/degraded
  - _Requirements: 2.1, 2.6, 4.3, 4.5, 4.6, 7.1_

- [x] 5. 筛选点评服务
  - 新建 `backend/app/services/insights/screener_review.py`：`build_screener_context`（每标的精确财务+价格）+ `review_hits` 调 AI，存 `InsightDocument(SCREENER_REVIEW)`
  - 提示强制多空/风险/待调研、禁买卖结论、附免责声明
  - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6_

- [x] 6. 价格提醒服务
  - 新建 `backend/app/services/insights/price_alerts.py`：`evaluate_price_alerts(session)`，对持仓∪关注标的比对 journal target/stop 与最新价，dedup_key 去重，写 `PriceAlert`
  - i18n 文案在前端侧渲染（后端存结构化字段）
  - _Requirements: 11.1, 11.4, 11.5_

- [x] 7. 文档清理
  - 新建 `purge_old_documents(session, days=90)` 于 insights 服务；删除超期 `InsightDocument`，记日志
  - _Requirements: 7.6_

- [x] 8. API：insights / screener / alerts / admin 扩展
  - 新建 `backend/app/api/insights.py`：文档列表/详情/下载(text/markdown)/标记已读/未读数；config GET+PUT；日报手动生成（BackgroundTasks）
  - 新建 `backend/app/api/screener.py`：规则 CRUD、`/screener/run`、`/screener/review`
  - 新建 `backend/app/api/alerts.py`：价格提醒列表/标记已读/手动评估
  - 扩展 `backend/app/api/admin.py`：`/admin/seed-universe`、`/admin/universe-status`
  - 在 `app/main.py` 注册新路由（带 api_prefix）
  - _Requirements: 1.2, 1.3, 1.8, 3.1, 3.4, 3.5, 4.2, 5.6, 8.1, 8.2, 8.3, 8.4, 11.2, 11.3_

- [x] 9. 调度集成
  - 扩展 `backend/app/services/data_sync/scheduler.py`：按 `ReportConfig.schedule` 注册每市场日报 cron；每日 4:00 清理 job；`_run_market_sync` 后调用 `evaluate_price_alerts`；提供 `reschedule_reports()` 供配置更新调用
  - config PUT 后触发 reschedule（调度未启用时静默跳过）
  - _Requirements: 3.6, 4.1, 4.4, 7.6, 11.5_

- [x] 10. 股票池扩充
  - 新建 `backend/scripts/seed_universe.py`：各市场精选成分股清单，复用登记+sync+financials，分批/重试/失败跳过/幂等
  - admin API 后台触发 + universe-status 完备度
  - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 10.6, 10.7_

- [x] 11. 后端测试
  - `backend/tests/` 增：筛选引擎、日报上下文（异动/触价/空数据）、价格提醒去重、文档清理 90 天边界、降级路径
  - 运行 `pytest` 全绿
  - _Requirements: 5.4, 4.5, 7.6, 11.4_

- [x] 12. 前端依赖与 i18n
  - `frontend/package.json` 增 `react-markdown`、`remark-gfm`、`rehype-sanitize`
  - `lib/i18n/messages.ts` 增 `insights.*`/`screener.*`/`alerts.*` 三语键
  - 新增 hooks：`useInsightDocuments`、`useInsightDoc`、`useReportConfig`、`useScreener`、`usePriceAlerts`、`useUnreadInsights`
  - _Requirements: 8.5, 1.1_

- [x] 13. 前端页面：AI 洞察列表与详情
  - `app/insights/page.tsx`：类型/市场过滤、分页、未读标记、下载
  - `app/insights/[id]/page.tsx`：react-markdown + remark-gfm + rehype-sanitize 安全渲染，站内 /stocks/{id} 链接放行，下载按钮
  - 空状态引导
  - _Requirements: 1.2, 1.3, 1.4, 1.5, 1.6, 1.8_

- [x] 14. 前端页面：日报配置
  - `app/insights/config/page.tsx`：市场多选/各市场时间/异动阈值/详略/语气/语言/重点关注文本/约束清单；保存调用 PUT
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

- [x] 15. 前端页面：规则筛选 + 点评
  - `app/insights/screener/page.tsx`：条件构建器（字段/运算符/值）、保存规则、运行结果表（命中值 + 数据缺失标注 + 规则原文）、"请 AI 点评"→ 生成文档并跳详情
  - _Requirements: 5.1, 5.2, 5.5, 5.6, 6.1, 6.4_

- [x] 16. 前端：导航与顶栏聚合
  - 侧栏 `sidebar.tsx` 新增"AI 洞察"分组（日报/筛选），命令面板补导航项，"AI 洞察"入口未读点
  - 顶栏 `topbar.tsx` 铃铛聚合复盘提醒 + 价格提醒，未读合并计数，点击跳转，标记已读
  - _Requirements: 1.1, 1.7, 11.2, 11.3, 11.6_

- [x] 17. 验证、提交与部署
  - 前端 `tsc --noEmit` + 后端 `pytest`；本地冒烟（import/路由注册）
  - git 提交（feat: AI 洞察中心）
  - scp 同步到服务器 `/opt/tradeai`，重建镜像，跑 alembic 迁移，重启容器
  - 服务器冒烟：健康检查、关键页面 200、手动触发一篇日报 + 一次筛选 + 一次股票池导入验证端到端
  - _Requirements: 9.1, 9.5, 9.7, 10.1_

## Task Dependency Graph

```json
{
  "waves": [
    { "wave": 1, "tasks": ["1"] },
    { "wave": 2, "tasks": ["2", "3", "6", "7", "10"] },
    { "wave": 3, "tasks": ["4", "5"] },
    { "wave": 4, "tasks": ["8", "11"] },
    { "wave": 5, "tasks": ["9", "12"] },
    { "wave": 6, "tasks": ["13", "14", "15", "16"] },
    { "wave": 7, "tasks": ["17"] }
  ],
  "dependencies": {
    "1": [],
    "2": ["1"],
    "3": ["1"],
    "4": ["3"],
    "5": ["2", "3"],
    "6": ["1"],
    "7": ["1"],
    "8": ["2", "4", "5", "6", "7"],
    "9": ["8"],
    "10": ["1"],
    "11": ["2", "4", "6", "7"],
    "12": ["8"],
    "13": ["12"],
    "14": ["12"],
    "15": ["12"],
    "16": ["12"],
    "17": ["9", "10", "11", "13", "14", "15", "16"]
  }
}
```

文字版（同上 JSON）：

```
1 (模型/迁移)
├─> 2 (筛选引擎)
├─> 3 (日报上下文/提示) ─> 4 (日报服务)
│                         └─> 5 (筛选点评, 也依赖 2)
├─> 6 (价格提醒)
└─> 7 (文档清理)

2,4,5,6,7 ─> 8 (API) ─> 9 (调度集成)
1 ─> 10 (股票池扩充, 依赖既有 discovery/sync)
2,4,6,7 ─> 11 (后端测试)

8 ─> 12 (前端依赖/i18n/hooks)
12 ─> 13 (列表/详情)
12 ─> 14 (配置)
12 ─> 15 (筛选/点评)
12 ─> 16 (导航/顶栏)

11,13,14,15,16,10 ─> 17 (验证/提交/部署)
```

## Notes

- 严格复用既有基础设施（ai_client/BudgetGuard/context_builder/discovery/sync/scheduler/i18n/统一响应壳），不引入常驻外部依赖。
- 所有 AI 产出走降级与免责声明；筛选过程零 AI。
- 数据库变更经 Alembic，部署时容器启动自动 `alembic upgrade head`。
- 服务器构建较慢（Next.js + 科学计算依赖），部署留足时间并分步验证。

