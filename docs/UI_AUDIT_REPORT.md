# SOC AI Platform — UI/UX Audit Report

> 审计范围：`/Users/levent/Desktop/Projects/sec/frontend`（40 个 page.tsx / 82 个组件文件 / 17,898 行页面代码）
> 技术栈：Next.js 16 App Router · React 19 · Tailwind 3.4 · next-intl · React Query · recharts · reactflow
> 审计阶段：**Phase 1 — 只审计，未修改任何 UI 代码**
> 审计日期：2026-09-11

---

## 0. 执行摘要

当前系统的真实状态可以概括为一句话：

> **底层设计令牌已经建好，但从未真正落地；产品骨架是一个功能齐全的安全后台，而不是一个 AI-Native 的 SOC 作战中心。**

上一轮改造已经写好了完整的 Design Token（Tailwind 扩展 + CSS 变量 + `styles/designTokens.ts`），但代码中实际使用语义令牌的比例只有 **8.7%**（657 处令牌 vs 6918 处硬编码色）。更严重的是，令牌层自身存在 **123 处"死类名"**——`text-text-muted`(74)、`bg-surface-ground`(35)、`bg-surface-canvas`(14) 在 `tailwind.config.ts` 中根本没有定义，生成的是空 CSS，静默失效。

AI 部分是最为核心的落差：后端 `AlertAnalysisResponse` 已经提供 `summary` / `evidence_points` / `recommended_actions` / `confidence` / `escalation_needed` / `entities` 全部真实结构化字段，前端 `lib/api/ai.ts` 也封装好了 `analyzeAlert` / `buildTimeline` / `generateReport`，但**这三个 API 全仓零调用**。AI 只是一个孤立的聊天页，业务页面 AI 渗透率为 0。

同时发现一处**明确的虚构数据**问题（monitor 页 4 个指标写死为 0，且该页 `apiStatus` 写死为 `healthy`），这与"不虚构数据"原则直接冲突，必须在改造中优先处理。

### 问题统计

| 级别 | 数量 | 定义 |
| --- | --- | --- |
| **P0 Critical** | **9** | 阻断产品成为企业级 AI-Native SOC，或存在数据真实性 / 安全操作缺陷 |
| **P1 High** | **16** | 显著影响一致性、可信度、核心任务效率 |
| **P2 Medium** | **14** | 体验瑕疵、技术债、可维护性风险 |
| **P3 Low** | **6** | 打磨项 |

---

## 1. 项目现状基线

### 1.1 已具备的良好基础（改造时应保留）

| 项 | 状态 |
| --- | --- |
| Design Token 定义 | ✅ `tailwind.config.ts` + `globals.css` + `styles/designTokens.ts` 三层齐全 |
| 字体层级 | ✅ `display/h1/h2/h3/body/small/caption` 7 级已定义（22/18/15/13/12/11px） |
| Spacing Scale | ✅ 4/8/12/16/20/24/32/40/48 已定义 |
| Radius | ✅ xs4 / sm6 / md8 / lg12 / xl14 已定义 |
| Shadow | ✅ subtle/sm/md/lg/elevated 已定义（克制，无滥用） |
| Dark Mode 机制 | ✅ `class` 模式 + SSR 防闪烁脚本 + CSP nonce，实现正确 |
| PageHeader 复用 | ✅ 35/40 页面统一使用 |
| i18n 键完整性 | ✅ 中英各 2020 叶键 / 77 命名空间，**双向缺失 0** |
| 敏感信息脱敏 | ✅ API Key 显示 `key_prefix***`，Secrets 用后端 `value_preview` |
| TypeScript | ✅ `tsc --noEmit` 基线通过（0 error） |
| 危险操作脱敏/权限 | ✅ 后端有 server-side page gate、短 JWT、CSRF |

### 1.2 关键量化指标

| 指标 | 实测值 | 目标 |
| --- | --- | --- |
| 硬编码色 : 语义令牌 | **6918 : 657（10.5 : 1）** | ≤ 1 : 5 |
| `severity-*` 令牌使用率 | **0 次**（改用 red/orange/amber 硬编码 2497 处） | 100% |
| 失效类名（生成空 CSS） | **123 处**（muted 74 / ground 35 / canvas 14）+ `animate-fadeIn` 4 | 0 |
| 手写 `<table>` : 复用 DataTable | **18 : 4** | ≤ 2 : 20 |
| `error.tsx` 覆盖 | 6 / 40 页面（15%） | 100% |
| `loading.tsx` 覆盖 | **0 / 40（0%）** | 100% |
| EmptyState 覆盖 | 4 / 40（10%） | 100% |
| Skeleton 覆盖 | 8 / 40（20%） | 100% |
| `aria-*` 属性 | 103 处，覆盖 34/143 文件（24%） | ≥ 90% |
| `role="tab"`/`tablist` | **0 处（全库）** | 全部 Tabs |
| focus trap | 仅 2 处（Modal / MobileDrawer） | 全部 Dialog/Drawer |
| 业务页面 AI 渗透 | **0 / 6 个核心业务页** | 全部 |
| 死代码组件 | **2858 行** `components/alerts/*` + 10 个孤儿组件 | 0 |

---

## 2. P0 — Critical

### P0-1 · 信息架构不是 Mission Control：无 Sidebar、无 Breadcrumb

**现状**：`ClientLayout.tsx` 只渲染 `<Navigation />`（顶部横向导航）+ `<GlobalSearch />`。全库无 `<aside>` 布局，**没有 Sidebar**。14 个导航项被压缩进顶部一条 `h-14` 的栏里，靠 3 个 hover 下拉分组（Analytics / Ecosystem / Admin）。

`components/common/Breadcrumbs.tsx` 已实现但 **0 引用**——面包屑体系形同虚设。

**影响**：
- 用户不知道"当前在哪"。SOC 的多层级结构（Operations → Alerts → Alert #123）完全无法体现。
- 顶部栏在 1366px 下已拥挤，英文 locale 需要靠 `compactNav`（`px-1.5` + `tracking-tight` + `text-xs`）硬挤，说明 IA 深度超出了顶部导航的承载能力。
- 无法承载"Investigation Workspace"这类需要持久侧栏的场景。

**建议**：引入 `AppShell = Header(56px) + Sidebar(240/64px 可折叠) + Content(max-w-[1600px])`。按用户手册建议的 7 组 IA 重排；Breadcrumb 进 Header 下方。

---

### P0-2 · AI 不是 Contextual：业务页面 AI 渗透率为 0

**现状**：全仓 AI 入口只有 3 处，且都指向同一个聊天页：
- `Navigation.tsx:137` → `/ai-assistant`
- `MobileDrawer.tsx:61` → `/ai-assistant`
- `GlobalSearch.tsx:46` → `/ai-assistant`

对 `app/[locale]/{alerts,assets,cases,playbooks,reports,threat-intel}` 与 `components/alerts/*` 全量 grep `AI|/api/ai|analyzeAlert` → **空**。

`lib/api/ai.ts:91-116` 的 `analyzeAlert` / `buildTimeline` / `generateReport` **全仓零调用**（死 API）。

**后端已就绪的真实能力**（`backend/routers/ai.py`）：

| 路由 | 行号 | 能力 |
| --- | --- | --- |
| `POST /ai/analyze-alert` | :135 | 返回 `AlertAnalysisResponse` |
| `POST /ai/query` | :185 | `intent/parameters/filter_criteria/response` |
| `POST /ai/recommend-playbooks` | :234 | Playbook 推荐 |
| `POST /ai/generate-report` | :415 | 报告生成 |
| `GET /ai/chat/stream` | :449 | SSE 流式 |

`backend/schemas/alert.py:105-125` 的 `AlertAnalysisResponse` **已包含全部结构化字段**：
`summary` · `evidence_points: list[str]` · `recommended_actions[]` · `confidence: int(0-100)` · `escalation_needed` · `ioc_count` · `entities` · `request_id`

前端 `lib/api/alerts.ts:51-62` 也已定义 `confidence` 类型。

**结论**：Evidence / Confidence / Recommendation / Human Approval 四类 UI **100% 可基于真实数据实现，目前实现度为 0**。这是本项目最大的未兑现价值。

---

### P0-3 · 设计令牌体系崩塌：123 处失效类名 + severity 令牌 0 使用

**实测**：

| 类名 | 使用次数 | 是否在 `tailwind.config.ts` 定义 |
| --- | --- | --- |
| `text-text-muted` | 74 | ❌ `text` 仅有 primary/secondary/tertiary/disabled/inverse/link/mono |
| `bg-surface-ground` | 35 | ❌ `surface` 仅有 page/card/hover/active/input |
| `bg-surface-canvas` | 14 | ❌ 同上 |
| `animate-fadeIn`（驼峰） | 4 | ❌ 仅有 `animate-fade-in` |
| **`bg-/text-/border-severity-*`** | **0** | ✅ 已定义 critical/high/medium/low/info，但无人用 |

**根因**：`tailwind.config.ts:11` 使用 `theme.extend`，Tailwind 默认调色板（gray/slate/white/black + 全部彩色）全部保留，无任何约束机制，开发者默认写 `text-gray-400`（527 次）、`text-white`（444 次）、`bg-gray-800`（275 次）。

`styles/designTokens.ts`（354 行三层令牌）**仅被** `lib/chartThemeAdapter.ts` 引用 5 次——令牌文件是"文档"而非真相源。

**影响**：主题切换不可靠、暗色模式约 50% 区域靠手写 `dark:` 补丁、severity 语义色出现三套并行实现。

---

### P0-4 · 告警详情页不是 Investigation Workspace

`app/[locale]/alerts/[id]/page.tsx`（755 行）实际结构：

```
Header(severity+status badge / title / source / time / assignee)
└ Description (:531)
└ Tabs[Overview | Timeline | Notes] (:546)
   └ Overview: 技术字段网格 (:577-589) → VirusTotal 外链 (:597) → IOCs (:615)
   └ 侧栏: TriagePanel (:636) → Quick Info (:643) → Threat Score (:673) → Affected Assets (:700)
```

对照 SOC 调查工作台的五个必答问题：

| 问题 | 覆盖 | 缺失 |
| --- | --- | --- |
| What happened? | 部分 | 仅 title/description，无攻击链叙述 |
| Why is it dangerous? | 部分 | 只有 threat_score 进度条，无风险理由 |
| What is affected? | **弱** | 仅 agent_name/IP 一张卡，**无 Entities 面板** |
| **What does AI think?** | **❌ 完全没有** | 无 AI 分析、无 Evidence、无 Confidence、无 Recommendation |
| **What should I do?** | **❌ 完全没有** | 无 Recommended Actions、无 Response 区 |

**缺失区块**：MITRE ATT&CK、Related/Correlated Alerts、Entities、Recommended Actions、Audit Trail。

**重大陷阱**：页面 :184-230 用了**页面内私有的局部 Timeline 组件**，而 `components/alerts/TimelineView.tsx` 是另一份实现——同名组件两份并存。

---

### P0-5 · `components/alerts/*` 2858 行 100% 死代码，且包含唯一的高危操作入口

8 个组件（`AlertActions` 418 / `AlertNotes` / `CorrelatedAlerts` / `CorrelationPanel` 363 / `MITREMapping` / `RealTimeAlertStream` / `ThreatIntelCard` / `TimelineView`）**全仓 import 命中 0**，只被 `FRONTEND_CODE_SPLITTING_GUIDE.md` 提及。

**后果极其严重**：
- `AlertActions.tsx:150/222-333` 是全项目**唯一**的 `isolate_host` / `block_ip` 实现 → 线上产品实际没有主机隔离 / IP 封禁入口。
- `MITREMapping.tsx`（56 处硬编码色）是唯一的 MITRE ATT&CK UI，同样未接入。
- `TimelineView.tsx` 是唯一完整 Timeline 实现，同样未接入。

**决策要求**：改造前必须先决策"复活"还是"删除"。这直接决定 Phase 5 的工作量。

---

### P0-6 · 虚构数据：monitor 页硬编码指标 + 假时间范围控件

**违反"不要虚构数据"原则，必须优先修复。**

| 位置 | 问题 |
| --- | --- |
| `monitor/page.tsx:130-138` | `malicious/suspicious/benign/unknown` **全部写死 `0`**，后端无此字段 |
| `monitor/page.tsx:183` | `apiStatus="healthy"` **硬编码**，不反映真实请求失败（首页至少用 `isError`） |
| `AlertTrendsChart.tsx:104-129` | 7d/30d 切换**只改本地 state**，`useDashboardStats` 无 period 参数，后端恒返 7 天 → 点 30d 图形不变，是**假控件** |
| `IOCStats.tsx:134` | 饼图 `filter(value>0)` 后恒空，且该组件 **239-266 无空状态** → 永久渲染一个空 PieChart |
| `IOCStats.tsx:171-173` | `threatPercentage` 恒为 0 → "Threat Level" 永久显示绿色 0.0% |
| `monitor/page.tsx:297` | `breakdown` 从未传入 → "Breakdown by Type" 永久空白 |
| `ResourceChart.tsx:37-42` | `all` 与 `24h` 同为 1440，时间范围无意义 |

**注**：未发现写死的告警数、风险分、AI 置信度或假趋势数组——所有 Dashboard 统计均真实来自 `GET /api/v1/dashboard/stats`。问题集中在 monitor 页。

---

### P0-7 · 危险操作 UI 缺失：无影响说明、无破坏性确认、无真实入口

| 操作 | 位置 | 二次确认 | 影响说明 |
| --- | --- | --- | --- |
| 删除告警 | `alerts/page.tsx:410→956` | ✅ ConfirmDialog | ❌ 仅通用文案，未说明不可恢复 |
| 批量改状态 | `alerts/page.tsx:381-406` | ❌ **无** | ❌ 无 |
| 状态流转 | `alerts/[id]/page.tsx:406` | ❌ **无** | ❌ 无 |
| 隔离主机 / 封禁 IP | `alerts/AlertActions.tsx:150,222-333` | ⚠️ 有 Dialog | ❌ **无影响说明**；确认按钮用 `bg-blue-600`(:324) 而非危险色；无输入名称确认 |
| 执行 hunt / playbook | `threat-hunting/page.tsx:185` | ❌ **无** | ❌ 无 |

AlertActions 的 Dialog 虽存在，但**它在死代码里**（见 P0-5）。

---

### P0-8 · 三态覆盖崩溃：34 页无 error.tsx、0 个 loading.tsx

| 态 | 覆盖 | 说明 |
| --- | --- | --- |
| `error.tsx` | 6 / 40（15%） | 仅 admin / ai-assistant / alerts / playbooks / settings / root |
| `loading.tsx` | **0 / 40** | 无流式 Suspense |
| ErrorBoundary | 0 页面主动使用 | `RouteErrorBoundary` 仅被 5 个 `error.tsx` 用 |
| EmptyState | 4 / 40（10%） | `components/EmptyState.tsx` **不在 `common/` 下**，可发现性差 |
| Skeleton | 8 / 40（20%） | 其余靠 54 处裸 `animate-spin` |
| 硬编码 "Loading..." | 1 | `settings/api-keys/page.tsx:171`，整页加载无页头无骨架 |

---

### P0-9 · 深色模式硬伤：卡片与背景同色不可辨

| 位置 | 问题 |
| --- | --- |
| `threat-intel/page.tsx:87,93,168` | 根背景 `dark:bg-gray-900`，卡片与结果卡**同为 `dark:bg-gray-900`** → 卡片完全不可辨 |
| `CorrelationPanel.tsx` | 363 行，**0 个 `dark:` 变体**，全裸 `gray-*` → 深色模式必然不可读 |
| `monitor/page.tsx:179,164,267,289` | 根 `dark:bg-slate-950` + 骨架 `dark:bg-slate-800` + 卡片 `dark:bg-gray-800` → 三套暗色灰阶混用 |
| `MITREHeatmap.tsx` | 16 处 hex 通过 inline style 注入，**无法主题化** |
| `RiskScore.tsx` / `TimeDisplay.tsx` | 硬编码 4/1 处，**0 个 `dark:`** |

---

## 3. P1 — High

| # | 问题 | 关键证据 | 影响 |
| --- | --- | --- | --- |
| P1-1 | **组件重复实现** | 4 套 Modal（`common/Modal` 137行带 focus trap / `ConfirmDialog` 98行无 trap / `ImportAlertModal` / `useUserModals`）；5 套 Loading（`LoadingState` / `LoadingSpinner` / `PageLoader` 0引用 / `LoadingProvider` 0引用 / `Skeleton`）；2 套 Tabs（`ui/Tabs` **0引用** / `TabTransition` **0引用**，页面全手写）；3 套 severity 色板（`ui/Badge:24` ≡ `AlertStatusBadge:91` 逐字相同，`DataTable:273` 是唯一正确委托方）；2 套 Timeline | 维护成本翻倍，样式必然漂移 |
| P1-2 | **表格未统一** | `DataTable` 仅 4 处使用；手写 `<table>` 18 个文件。分页器/空态/行高存在三套标准；手写表全部 0 个 `aria`，无 `<th scope>` | 一致性 + 无障碍双失 |
| P1-3 | **Toast 无严重度分级 + 无通知中心** | `Toast.tsx:7` 类型仅 `success/error/warning/info`，**无 critical**；唯一区分是 error 用 `aria-live="assertive"`(:71)。无铃铛/抽屉/历史/未读。4000ms 硬编码(:54)，无队列上限无去重。颜色硬编码 green/red/blue/yellow 绕过 success/danger 令牌。`stores/notificationStore.ts`（89 行 Zustand）**零引用**，是第二套并行实现 | Critical Alert 无法与普通通知区分 |
| P1-4 | **Command Palette 是假的** | `GlobalSearch.tsx:26-68` 是**静态 8 项数组**，过滤仅 `title.toLowerCase().includes()`(:73-75)。**不搜 alerts/assets/IOC/users/playbooks**，无 API 调用，无快捷动作。却提示 "Try searching for alerts, playbooks, or settings"(:185) —— **名不副实**。全部文案硬编码英文（:129/133/142/151/182/185/205） | 用户被误导 |
| P1-5 | **i18n：键全齐，UI 大量绕过** | 中英键 100% 对齐，但硬编码严重：`Navigation.tsx:462` "API OK"/"Err"、`GlobalSearch.tsx` 全英文、`ai-assistant/` 56 处硬编码中文（`ChatInput` 19 / `HeroPrompts` 20 / `ChatHistoryPanel` 7 / `ChatMessages` 6 / `ChatHeader` 4）、`playbooks/page.tsx:184` "Max concurrent:" / `:241` "Auto-refresh ON (10s)" / `:362-368` "Showing X to Y of Z"、`settings/page.tsx:54-57` 内联 `isZh ? "中文" : "English"`、`login/page.tsx:226-258` locale 三元、`cases/page.tsx:495,506` "← Prev"/"Next →"、`alerts/[id]:414,431` `Status changed to "${...}"` | 中英混排 |
| P1-6 | **根背景 5 种互不一致** | `bg-gray-50 dark:bg-gray-900`（17 页）/ `bg-surface-ground`（5 页，**未定义**）/ `bg-surface-canvas`（3 页，**未定义**）/ `bg-surface-page`（2 页）/ `bg-gray-50 dark:slate-950`（1 页，monitor） | 页面间背景跳变 |
| P1-7 | **间距不统一** | 主区 `py-4` ×67 / `py-8` ×38 / `py-6` ×16 / `py-12` ×6；底部 `pb-12` vs `pb-16` vs 无 | 视觉节奏混乱 |
| P1-8 | **AI 助手页：伪流式 + 硬编码营销文案 + 过度炫酷** | `useAIChat.ts:60-76` `typeWriterEffect`（3 字符/15ms 模拟打字机）在 SSE 失败时**伪装流式**；`HeroPrompts.tsx:126-127` 写死"毫秒级极速响应 · 200K 超长日志深度推理"；`ChatInput.tsx:184-211` 模型名 `"Llama 3.2 11B"` 等按 `model.id.includes()` 字符串硬匹配；发送按钮三色渐变 `from-blue-600 via-indigo-600 to-purple-600`(:355)、渐变文字 `bg-clip-text`(:117)、`shadow-xl shadow-indigo-500/20 ring-4`、`animate-pulse` 滥用、`tailwind.config.ts:190` 预置 `shadow-glow` —— 与 config 自注"禁止荧光色"矛盾 | 可信度受损 + 违反"克制"原则 |
| P1-9 | **AI 助手缺 Stop / Retry** | 全目录 grep `abort/stop` 为空，无 `AbortController`，SSE `reader` 无法取消；grep `retry/regenerate` 为空，错误仅 push 一条硬编码英文气泡(:278-285) | 长响应无法中断 |
| P1-10 | **AI 输出零结构化** | `types.ts:3-10` 的 `Message` 仅 5 字段，连 `id` 都没有（`key={index}`，`ChatMessages.tsx:135`）。`ChatMessages.tsx:189-255` 直接 `ReactMarkdown` 整段渲染。唯一结构化尝试是 `parseThinkingContent()`(:73-99) 靠正则硬拆 `<think>` 标签（split 正则含 `[A-Z\u4e00-\u9fa5]{2,}`，极脆弱）。Analysis/Evidence/Confidence/Recommendation/Approval 全部未分层 | 无法满足 AI UX 要求 |
| P1-11 | **AI 置信度无可视化、无缺失态** | 置信度仅 4 处、`correlation/page.tsx:356` 真实渲染 `{confidence_score*100}%`，其余 3 处均在死代码中。**无进度条、无配色分级、无"低置信度"警示**；未做 "Confidence unavailable" 兜底（后端 `ai_service_enhanced.py:297` 降级模式一律 `confidence=0.6`，UI 不区分） | 违反 AI 透明度要求 |
| P1-12 | **Dashboard 缺 "What should I do next"** | Quick Actions 是**静态导航**（`page.tsx:341-407`），无数据驱动的下一步建议。缺 MTTD、SLA 违约、环比增速。`StatCard` 支持 `trend` prop（`StatCard.tsx:16-22`）但 **8 处调用全部未传**，功能死掉 | 指挥中心不指挥 |
| P1-13 | **首页与 monitor 页是两套重叠 Dashboard** | `page.tsx`（412 行，7 区块）与 `monitor/page.tsx`（305 行，4 KPI + 图表 + MITRE + AssetRisk）调同一接口，信息重复、视觉不同 | 用户困惑 |
| P1-14 | **图表问题** | 首页趋势是**手写 div 柱状图**(`page.tsx:172-196`)，无 Tooltip 组件仅有 `title` 属性；5 处重复 `MutationObserver` 检测暗色（AlertTrendsChart:51 / SeverityDistribution:48 / TrendsChart:59 / ResourceChart:71 / SeverityPieChart:43）；`MITREHeatmap:268-328` 战术详情列表与矩阵**完全重复**；`MITREHeatmap.tsx:161` `min-w-[1400px]` 移动端需横向拖 14 列，**实际不可用** | 图表价值低 + 移动端崩 |
| P1-15 | **Assets 页是纯 CRUD，无 Asset Risk** | 字段仅 hostname/ip/owner/business/criticality/tags/notes/is_active（`assets/page.tsx:336-345`），**无风险分、漏洞数、关联告警、最后上线、安全状态**。含 `risk_score` 的 `AssetRiskTable` **只在 monitor 页用** | 资产页不体现风险 |
| P1-16 | **Reports 无 Executive Summary / 无 PDF / 无分享** | `reports/page.tsx` 仅：输入 alertId → 调 `/api/generate-report` → 三份模板文本 → 复制到剪贴板(:103-107)。`Download` 图标 import 于 :10 但**全文件未使用**。`messages/en.json` **已定义** `reports.download/pdf/html/csv/sharing/history/format` 键，UI 全部未实现。唯一导出在 `threat-intel/dashboard:221` 且仅 JSON | 无法汇报管理层 |

---

## 4. P2 — Medium

| # | 问题 | 证据 |
| --- | --- | --- |
| P2-1 | **排序是纯客户端，只排当前页 20 条** | `alerts/page.tsx:344-360`，非全量排序，**严重误导** |
| P2-2 | 搜索不走 URL query，刷新即丢筛选 | `alerts/page.tsx:301-311` 防抖 400ms |
| P2-3 | `sourceFilter` 是死状态 | `alerts/page.tsx:291` 有 state，**渲染层无对应 UI**；文件头注释第 8 行声称有 "source type, time range" |
| P2-4 | 风险阈值三套不一致 | 首页 `page.tsx:318-322`（≥70/40）、`AssetRiskTable:25-29`（80/60/40/20）、`RiskScore:18-20`（40/70） |
| P2-5 | 移动端表格仅 `overflow-x-auto`，无卡片降级 | assets / admin-users / api-keys / triggers 的 `sm:` 断点仅 1-2 处；**correlation 与 threat-hunting 完全无移动端方案** |
| P2-6 | `admin/audit` 是 1 行 re-export | `app/[locale]/admin/audit/page.tsx:1` → `export { default } from "@/app/[locale]/audit/page"` |
| P2-7 | Settings hub 制造孤儿路由 | `settings/page.tsx:77,104` 只链接 api-keys 与 audit，**未链接 ai-models 与 notifications** |
| P2-8 | **无障碍：全库无 `role="tab"`/`tablist"`** | Tabs（`alerts/[id]:552`、`correlation:175`）无 role、无方向键导航；排序表头是普通 `<button>`，缺 `aria-sort`（alerts:476/502/536）；筛选下拉 `FilterDropdown`(153-224) 无 `role="menu"`、无 Esc 关闭、无焦点管理；`ai-assistant/` 整个目录 aria 计数为 **0** |
| P2-9 | **无 `prefers-reduced-motion` 全局降级** | `globals.css` 全文 0 命中 |
| P2-10 | Toast 无队列上限/去重/持久化 | `Toast.tsx:54` |
| P2-11 | 10 个孤儿组件 | `ui/Tabs` / `ui/Divider` / `common/Breadcrumbs` / `common/PageLoader` / `common/RippleButton` / `common/LoadingProvider` / `common/TabTransition` / `common/FadeIn` / `components/ChatHistorySidebar`(17.8KB) / `components/QuickActions` |
| P2-12 | `components/ui/` 无 `index.ts` | 17 个文件只能深路径导入；与 `components/common/` 职责边界未定义，无 lint 约束 |
| P2-13 | Playbook DAG 无语义可视化 | `DAGCanvas.tsx:23-25` 只注册单一 `dagNode` 类型，`DAGNode.tsx:86-90` 只渲染 label+stepId，**不按节点类型区分图标/配色**。类型体系是 15 种具体 action（`constants.ts:65-80`），非 Trigger→Condition→Action→Approval→Result 五类抽象。无节点重试入口、无执行日志面板；`cancelled` 被降级为 `skipped`(`[id]:335`)；MiniMap 与边色硬编码 hex。✅ 有 6 种实时状态 + 5s 轮询 + 运行中边动画 |
| P2-14 | 页头字号不一致 | `login/page.tsx:176` 用 `text-2xl`，`PageHeader.tsx:43` 用 `text-xl sm:text-2xl` |

---

## 5. P3 — Low

| # | 问题 | 证据 |
| --- | --- | --- |
| P3-1 | `html { font-size }` 随断点变化（14→15→16px），与 Tailwind 默认 rem 体系耦合，间距计算非整数 | `globals.css:196-208` |
| P3-2 | `--spacing-*` CSS 变量与 `tailwind.config.ts` spacing 重复定义，两份已存在漂移风险 | `globals.css:78-90` vs `tailwind.config.ts:130-142` |
| P3-3 | `login/page.tsx:154` "SOC Platform v2.0" 硬编码版本号 | — |
| P3-4 | 中文注释集中在少数文件 | `playbooks/create/page.tsx` ×59、`TwoFactorSettings.tsx` ×28、`MITREHeatmap.tsx` ×23 |
| P3-5 | `ResourceChart.tsx` 有 `all`/`24h` 同为 1440 的无效时间范围 | `ResourceChart.tsx:37-42` |
| P3-6 | `themeColor` 硬编码 `#f8fafc`/`#1e293b`，未与 CSS 变量联动 | `layout.tsx:82-85` |

---

## 6. UI Consistency Matrix

✅ 已用统一组件　⚠️ 部分/不一致　❌ 缺失或各页自造

| 维度 | Alerts | Cases | Assets | Playbooks | Reports | ThreatIntel | Wazuh | AI |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| PageHeader | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | — 无此页 | ⚠️ 自造 |
| 根背景令牌 | ⚠️ ground(死) | ⚠️ ground(死) | ❌ gray-50 | ⚠️ 3 种 | ⚠️ ground(死) | ❌ gray-50 | — | ⚠️ gray-850 |
| Search | ✅ | ⚠️ | ⚠️ | ⚠️ | ❌ | ✅ | — | ❌ |
| Filter | ⚠️ 缺 asset/time | ⚠️ | ❌ | ⚠️ | ❌ | ⚠️ | — | ❌ |
| Table | ✅ DataTable | ✅ DataTable | ❌ 手写 | ❌ 手写 | ❌ 无表 | ❌ 手写 | — | ❌ |
| Drawer/Modal | ⚠️ 自造 | ❌ | ⚠️ | ⚠️ 自造 | ❌ | ❌ | — | ❌ |
| Badge 体系 | ⚠️ 2 套 | ⚠️ | ❌ 自造色板 | ❌ 自造色板 | ❌ | ❌ | — | ❌ |
| Empty State | ✅ | ✅ | ⚠️ | ⚠️ | ✅ | ⚠️ | — | ⚠️ |
| Loading | ✅ Skeleton | ✅ | ⚠️ | ⚠️ | ❌ 无骨架 | ⚠️ | — | ✅ |
| Error | ✅ error.tsx | ❌ | ❌ | ✅ | ❌ | ❌ | — | ✅ |
| 移动端 | ✅ 双套 | ✅ 双套 | ⚠️ overflow | ⚠️ overflow | ⚠️ | ⚠️ | — | ✅ |
| dark 变体 | ⚠️ 26/32 | ⚠️ 17/32 | ⚠️ | ⚠️ | ⚠️ | ❌ 同色 bug | — | ✅ |
| AI 区块 | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | — | ⚠️ 仅聊天 |

**说明**：系统**无 Wazuh 前端页面**。后端有完整 Wazuh 集成（`backend/routers/alert_stream.py:30` `/api/v1/wazuh/stream`、`backend/services/alerting/alert_stream_service.py`、`backend/config/wazuh`、`docs/wazuh_integration.md`、`.env.wazuh`），前端仅有 `lib/alertWebSocket.ts:53 WazuhWebSocketClient` 数据流客户端。用户手册第 16 节的 Wazuh UI 优化**需先创建页面**，不属改造范围。

---

## 7. 改造优先级建议（Phase 2 起）

### 必须先决策的 3 件事

1. **`components/alerts/*` 2858 行**：复活（接入告警详情页）还是删除？→ 决定 Phase 5 工作量（建议：复活 `MITREMapping` / `TimelineView` / `ThreatIntelCard` / `AlertActions`，删除其余）
2. **monitor 页**：与首页合并，还是改造为"深度运营视图"？→ 决定 Phase 4 结构
3. **Wazuh**：是否需要新建前端页面？→ 后端已就绪，前端为 0

### 建议的 Phase 排序（基于投入产出比）

| 顺序 | Phase | 理由 |
| --- | --- | --- |
| 1 | **Design System 收敛** | 所有后续工作的地基。补 `text-muted`/`surface-ground`/`surface-canvas` 定义（123 处立刻生效）、启用 `severity-*`、加 lint 规则禁裸色、收敛 3 套 severity 色板到 `ui/Badge` |
| 2 | **Layout / Navigation 重构** | AppShell + Sidebar + Breadcrumb。P0-1，影响全部 40 页 |
| 3 | **虚构数据清理**（monitor 页） | P0-6，可信度问题，工作量小（约 0.5 天） |
| 4 | **通用组件库统一** | 4 套 Modal→1、5 套 Loading→2、手写 table→DataTable、补 EmptyState/LoadingState/ErrorState 三件套 |
| 5 | **Alerts + Alert Detail** | P0-4/5/7，SOC 核心任务流 |
| 6 | **AI Contextual 化** | P0-2，后端已就绪，是最大未兑现价值 |
| 7 | Dashboard → Assets → Playbooks → ThreatIntel → Reports → Settings/Admin |
| 8 | Command Palette / Notification Center / 三态补齐 |
| 9 | Responsive / Dark / A11y / Performance / 回归 |

---

## 8. 验收基线（改造后必须回归）

当前基线已记录，改造后不得低于此线：

| 项 | 基线 |
| --- | --- |
| `tsc --noEmit` | ✅ 0 error |
| i18n 中英键对齐 | ✅ 双向 0 缺失（2020 叶键 / 77 命名空间） |
| 敏感信息脱敏 | ✅ API Key / Secrets 均已脱敏 |
| 页面总数 | 40 个 page.tsx，17,898 行 |
| 后端 API Contract | **禁止修改** |

---

*本报告由 UI/UX 审计生成，未修改任何代码。*
