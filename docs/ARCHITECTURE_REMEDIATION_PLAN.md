# SOC Copilot 架构整改计划方案

> **版本**: v2.0 | **日期**: 2026-06-17 | **基准分支**: `ui/p0-p2-optimizations`
> **状态**: 可执行 | **变更**: 本版吸收了 v1.1 评审的 6 项结论，重写为干净执行版（见附录 A 变更记录）

---

## 目录

1. [执行摘要](#1-执行摘要)
2. [问题清单](#2-问题清单)
3. [原则与总体路线](#3-原则与总体路线)
4. [P0 — AI 层运行时缺陷修复](#4-p0--ai-层运行时缺陷修复)
5. [P1 — 后端分层统一](#5-p1--后端分层统一)
6. [P2 — Playbook 引擎收敛](#6-p2--playbook-引擎收敛)
7. [P3 — 前端状态与数据层收敛](#7-p3--前端状态与数据层收敛)
8. [P4 — CI 安全门禁化](#8-p4--ci-安全门禁化)
9. [里程碑与排期](#9-里程碑与排期)
10. [风险与回滚](#10-风险与回滚)
11. [验收标准与度量](#11-验收标准与度量)
12. [附录 A：v2.0 变更记录](#12-附录-av20-变更记录)

---

## 1. 执行摘要

架构审查识别出 **5 类架构债**，含 **3 个 AI 层运行时缺陷**。本计划按优先级分 5 阶段推进。经代码级评审核实，相对初版方案有两处实质性调整：

- **P0 影响面扩大**：缺陷位于 `LLMRetryService`，它是 `AlertService`/`TimelineService`/`ReportService`/`AITaskService` **4 个核心服务的统一 LLM 入口**，而非边缘任务队列问题。`get_model_name()` 崩溃影响"告警分析"主链路成功路径。
- **P2 路线需先决策**：v6 与 v7 引擎的 registry 返回**不同构的执行模型**（`BaseStep` vs `BaseNodePlugin` + 不同 Context），"换 import 即收敛"不可行。需在执行前决策"单引擎收敛"（5-7 周，高风险）或"双引擎派发"（2-3 周，务实）。

其余（P1 后端分层、P3 前端、P4 CI 门禁）方向与初版一致，仅做精度修正和去过度设计。

### 关键路径

```
M0(P0验证+修复) → M2/M3(P1分层) → M0.5(P2决策) → M4/M5(P2执行)
                                                              约 8 周（双引擎）或 11 周（单引擎）
P3(前端) ∥ P4(CI门禁) 可随时并行
```

---

## 2. 问题清单

| ID | 问题 | 严重度 | 证据（已核实） | 章节 |
|----|------|--------|--------------|------|
| **P0-1** | `ai_task_service.py:208` 调用不存在的 `.generate()` | 🔴 运行时 | else 分支（REPORT_GENERATION / CHAT_COMPLETION）必崩 | §4 |
| **P0-2** | `llm_retry.py:240` 调用不存在的 `.get_model_name()` | 🔴 运行时 | 4 个核心服务的 LLM 成功路径必崩 | §4 |
| **P0-3** | `response_class=dict` 破坏 pydantic 校验链 | 🔴 运行时 | 注释"handled by llm_retry"经核实为**错误注释**，dict 传到 `model_json_schema()` 必崩 | §4 |
| **P1-1** | 17 个路由直接操作 session（**88 处**，top1 `security_alerts`=20） | 🟥 架构债 | `grep -rcE "session\.(execute\|add\|...)"` 精确统计 | §5 |
| **P1-2** | 6 个域缺失 Repository | 🟥 架构债 | SecurityAlert/BlockedIP/CorrelatedEvent/Rule/MonitorHistory/Alerts | §5 |
| **P1-3** | `auth.py`/`playbook_definitions.py` 内联大量业务逻辑 | 🟥 架构债 | 180+ 行密码/锁定逻辑、200+ 行 markdown 生成 | §5 |
| **P1-4** | `alert_stream_service.py:14` 反向依赖 routers | 🟥 循环风险 | 唯一 sink 是 WebSocket | §5 |
| **P2-1** | Playbook 三套执行路径并存 | 🟥 架构债 | v6_linear/dag/v7_dag 均活跃 | §6 |
| **P2-2** | `adapter.py` 死桥接（零调用） | 🟧 死代码 | grep 全仓零 caller | §6 |
| **P3-1** | 前端 3 个 API 客户端并存 | 🟧 架构债 | api-client.ts 被死代码引用 | §7 |
| **P3-2** | 24 处裸 `fetch()` | 🟧 架构债 | 散在 app/ 和 components/ | §7 |
| **P3-3** | `usePermission` 不响应登录态 | 🟧 活跃缺陷 | 直接调 loadAuthState，未订阅 store | §7 |
| **P3-4** | `useCachedQuery` 死代码 | 🟧 死代码 | 7 派生 hook 零消费者 | §7 |
| **P4-1** | CI 安全扫描全 `continue-on-error` | 🟦 策略 | 6 个扫描器均不阻断 | §8 |

---

## 3. 原则与总体路线

### 3.1 五项原则

1. **优先级驱动**：运行时缺陷（P0）优先；架构债按依赖排序（P1 分层是 P2 的地基）。
2. **小步快跑**：单 PR 净变更 ≤ 400 行；每阶段可独立合并与回滚。
3. **测试先行**：被改模块先补测试（标定现状行为），再改实现。
4. **删除优先于新增**：先删零风险死代码释放复杂度，再做抽象。
5. **行为等价**：重构期不改对外 API 契约和业务语义。

### 3.2 关键决策点（需提前拍板）

**DP-1（P2 引擎路线，最关键）**——必须在 M0.5 里程碑决策：

| 路线 | 描述 | 工期 | 风险 |
|------|------|------|------|
| **A. 双引擎派发**（推荐） | 保留 v6（线性执行）+ v7（DAG 模式），建 adapter 按引擎版本派发；复用被删的 `adapter.py` 思路 | 2-3 周 | 低 |
| B. 单引擎收敛 | 把 v6 完全迁到 v7 执行模型，删 v6 | 5-7 周 | 中-高 |

推荐 A 的理由：v6 被 dag/engine 当步骤库、且 runs/approvals 路由直连，活跃度远超普通死代码；强行收敛需重写 dag/engine 执行核心（v6 `BaseStep` 与 v7 `BaseNodePlugin` + `NodeExecutionContext` 不同构），性价比低。

---

## 4. P0 — AI 层运行时缺陷修复

### 4.1 缺陷确认（已代码级核实）

`EnhancedAIService` 当前公开方法：`generate_structured`、`analyze_alert_with_rag`、`natural_language_query`、`recommend_playbooks`、`chat`、`generate_investigation_report`。**无 `generate()`，无 `get_model_name()`**。

| 缺陷 | 位置 | 触发条件 | 影响面 |
|------|------|---------|--------|
| P0-1 | `ai_task_service.py:208` `.generate()` | `AITaskType` 为 REPORT_GENERATION / CHAT_COMPLETION（else 分支） | AI 任务队列 |
| P0-2 | `llm_retry.py:240` `.get_model_name()` | **任何**经 `LLMRetryService` 的 LLM 调用成功后 | **4 个核心服务**：AlertService（告警分析）、TimelineService、ReportService、AITaskService |
| P0-3 | `ai_task_service.py:199-204` → `llm_retry.py:238` | ALERT/TIMELINE/IOC 任务类型（if 分支） | `dict` 传到 `.model_json_schema()` 必崩 |

> P0-3 澄清：初版曾怀疑 `response_class=dict` 是有意"无 schema 逃生口"。核实 `AITaskType` 枚举与注释后确认是**错误注释导致的真 bug**——`llm_retry` 根本不处理 dict。

### 4.2 修复方案：补齐 `EnhancedAIService` 缺失能力

```python
# services/ai_service_enhanced.py 新增
class EnhancedAIService:
    def get_model_name(self) -> str:
        """当前默认模型 ID（收编原 get_model_name）。"""
        return self._default_model_id

    async def generate(self, prompt: str) -> str:
        """简单文本生成（收编原 generate，供 CHAT_COMPLETION 等用）。"""
        provider = LLMFactory.create_provider_for_model(
            self._default_model_id, self._default_provider
        )
        resp = await provider.chat_completion(
            messages=[{"role": "user", "content": prompt}]
        )
        return resp["content"]
```

P0-3 修正（保留原语义，不擅自加 schema 约束）：

```python
# ai_task_service.py:199-204 —— 用真实 schema 或 None，不再传 dict
# ALERT/TIMELINE/IOC 三类本就各有响应结构，应传各自 schema
result = await llm_service.generate_structured(
    prompt=task.prompt,
    response_class=_SCHEMA_BY_TASK_TYPE[task.task_type],  # 真实 schema，非 dict
)
```

> 若 `AlertAnalysisResponse` 等 schema 尚未定义，则先定义；若确认某类是自由文本，传 `None` 并让 `LLMRetryService.generate_structured` 在 `None` 时跳过 schema 校验（在 §4.3 步骤 2 实现）。

### 4.3 执行步骤

| 步骤 | 动作 | 验证 |
|------|------|------|
| **0** | **前置验证**：核查部署环境 LLM provider 配置（`ANTHROPIC_API_KEY`/`ZHIPU_API_KEY`）；在测试环境用真实 provider 触发一次 `AlertService.analyze`，观察是否抛 `AttributeError`。确认线上是否真在崩。 | 若未崩 → P0 降为"P1 高优"，仍修但不挤占当天；若在崩 → 维持 P0 |
| 1 | 写测试：`test_enhanced_ai_service.py` 补 `get_model_name`/`generate`；`test_llm_retry.py` 补 `response_class=None` 跳过校验路径 | 先红 |
| 2 | 实现 `EnhancedAIService.get_model_name`/`generate`；让 `LLMRetryService` 支持 `response_class=None` | 单测转绿 |
| 3 | 写测试：`test_ai_task_service.py` 覆盖 if 分支（schema）和 else 分支（generate） | 先红 |
| 4 | 修正 `ai_task_service.py:199-210` 调用 | 单测转绿 |
| 5 | **集成测试**：`AlertService.analyze` 成功路径端到端通过（P0-2 影响面的核心验证） | 通过 |
| 6 | 顺手清理：删 `ai_service_enhanced.py:483-484` 遗留别名 `AIService`；删 `:189-201` 死 RAG 代码 | grep 确认无引用 |

### 4.4 工作量与风险

- **工作量**：1 人日（含步骤 0 验证）
- **风险**：低。纯能力补齐 + 方法对齐，不改外部契约。
- **回滚**：单 commit revert。

---

## 5. P1 — 后端分层统一

### 5.1 现状（已精确核实）

`AGENTS.md` 规定 `Router → Service → Repository → Model`，实际三种风格并存：

| 风格 | 占比 | 代表 |
|------|------|------|
| Router → Service → Repo | ~30% | `alert.py`, `assets.py` ✅ |
| Router → Repo（跳 Service） | ~40% | `auth.py`, `playbook_definitions.py` |
| Router → Session（跳两层） | ~30% | `security_alerts`(20处), `blocked_ips`(14), `monitor`(11) |

**88 处 session 直查分布在 17 个路由**。6 个域缺 Repository。`alert_stream_service.py:14` 反向依赖 `routers.websocket`（唯一 sink 是 WebSocket）。

### 5.2 方案

#### 5.2.1 补齐 6 个 Repository

```
backend/repositories/
├── security_alert_repository.py    ├── blocked_ip_repository.py
├── correlated_event_repository.py  ├── correlation_rule_repository.py
├── monitor_history_repository.py   └── monitoring_alert_repository.py
```

各 Repository 聚合 CRUD + 分页 + 该域特有查询，遵循现有 `repositories/base.py` 基类约定。

#### 5.2.2 为直连 session 的域补薄 Service

```python
# services/security_alert_service.py (新建)
class SecurityAlertService:
    def __init__(self, repo: SecurityAlertRepository, ws_manager: WebSocketManager):
        self._repo = repo
        self._ws = ws_manager   # 直接依赖，不引入 Protocol

    async def acknowledge(self, alert_id, user):
        alert = await self._repo.get(alert_id)
        alert.acknowledge(user.id)
        await self._repo.save(alert)
        await self._ws.publish(alert)
        return alert
```

#### 5.2.3 反向依赖的轻量解法（不引入 AlertSink 接口）

> **设计取舍**：初版拟引入 `AlertSink` Protocol。评审否定——WebSocket 是唯一 sink，为"未来可能的第二个 sink"建抽象属 YAGNI。

将 `get_manager()`/`push_alert` 从 `routers/websocket.py` **下沉到 `services/websocket_manager.py`**（它本就是 service 职责，放 router 是错位）。`alert_stream_service` 改 import 新位置，循环隐患根除，零新抽象。

```python
# 改造前
# services/alerting/alert_stream_service.py:14
from routers.websocket import get_manager, push_alert   # ← 反向依赖

# 改造后
from services.websocket_manager import get_manager, push_alert  # ← 正向依赖
```

#### 5.2.4 路由瘦身

`auth.py`（180 行密码/锁定逻辑）→ 抽 `AuthService`；`playbook_definitions.py`（200 行 markdown/IOC 提取）→ 抽 `ReportService` + `IocExtractor`。路由仅留：参数解析 → 调 Service → 响应映射。

### 5.3 增量执行（每域一 PR）

| 批次 | 域 | 动作 | 验收 |
|------|----|------|------|
| 1 | `blocked_ips` | Repo + Service + 迁移 14 处 | 路由 < 60 行，无 session 直查 |
| 2 | `security_alerts` + **websocket_manager 下沉** | Repo + Service + 迁移 20 处 + 解反向依赖 | 同上 |
| 3 | `monitor` + `monitoring_alerts` | 同上 | |
| 4 | `correlation` + `correlated_event/rule` | 同上 | |
| 5 | `auth` | 抽 `AuthService`，下沉密码/锁定逻辑 | 路由 < 80 行 |
| 6 | `playbook_definitions` | 抽 `ReportService` + `IocExtractor` | |

### 5.4 工作量与风险

- **工作量**：约 2 人周（去 AlertSink 后较初版降）
- **风险**：低-中。逐域迁移，每域独立可回滚；行为不变。
- **回滚**：按域 PR 粒度 revert。

---

## 6. P2 — Playbook 引擎收敛

### 6.1 现状（已核实，推翻"v6 是死代码"假设）

**三套活跃路径 + 一套死桥接**：

| 路径 | 规模 | 活跃入口 |
|------|------|---------|
| `v6_linear.engine` | 11 文件/1,578 行 | `runs.py`/`approvals.py` 路由 + 给 dag/engine 当步骤库 |
| `dag/engine` | 4 文件/~1,450 行 | `triggers/cron.py`/`webhook.py` |
| `v7_dag` + `DAGScheduler` | 18 文件/2,414 行 | startup 加载、`playbook_definitions.py` |
| `adapter.py` | 1 文件 | 💀 零调用（死代码） |

**关键纠缠**：`dag/engine.py:16` 硬编码 `from ..v6_linear.registry import get_registry`。**且 v6 `get_step_implementation` 返回 `BaseStep`，v7 `get_plugin` 返回 `BaseNodePlugin`（+ `NodeExecutionContext`），执行约定完全不同构**——不能简单替换。

### 6.2 路线 A（推荐）：双引擎派发

接受 v6（线性）/ v7（DAG）作为两种合法执行模式，用 adapter 按引擎版本派发。

| 步骤 | 动作 | 风险 |
|------|------|------|
| 1 | 删 `adapter.py` 死代码 + `__init__.py:9` re-export | 零（grep 确认零调用） |
| 2 | 新建 `playbook_engine/dispatcher.py`：按 `PlaybookRunModel.engine_version` 派发到 v6.engine 或 v7 DAGScheduler | 低，纯新增 |
| 3 | 让 `runs.py`/`approvals.py`/triggers 统一走 dispatcher（而非各自直连） | 中，逐入口迁移 + 回归 |
| 4 | 统一状态/进度/输出 schema（对外契约收敛，内部实现保留两套） | 中 |

**收益**：认知统一（调用方只看 dispatcher），但不动 v6/v7 内部实现，风险可控。

### 6.3 路线 B（备选）：单引擎收敛

把 v6 完全迁到 v7 执行模型。

| 步骤 | 动作 | 风险 |
|------|------|------|
| 1 | 删 `adapter.py` | 零 |
| 2 | dag/engine 引入 `StepProvider` seam，当前委托 v6 | 低（纯重构） |
| 3 | 实现 v7 `StepProvider` adapter：翻译 v6 调用约定 → v7 `NodeExecutionContext.execute()` | **高**，执行模型翻译，易引入语义偏差 |
| 4 | dag/engine 切到 v7 provider | 中 |
| 5 | 迁 `PlaybookRunService`；为所有 builtin playbook 写回归 | 中 |
| 6 | 删 `v6_linear/`（1,578 行） | 低（稳定后） |

**代价**：步骤 3 是重写 dag/engine 执行核心，工期翻倍。

### 6.4 工作量与风险

| 路线 | 工期 | 风险 |
|------|------|------|
| A. 双引擎派发（推荐） | 2-3 周 | 低 |
| B. 单引擎收敛 | 5-7 周 | 中-高 |

### 6.5 执行前置条件

**M0.5 设计评审**：决策 DP-1（路线 A/B）。建议在 M3（P1 完成）之后、P2 动工之前，用一次专门的设计评审对比两路线，再做选择。本计划默认按 A 编排排期。

---

## 7. P3 — 前端状态与数据层收敛

### 7.1 现状

| 维度 | 问题 |
|------|------|
| API 客户端 | 3 套：`api-client.ts`（强，仅被死代码用）、`api/client.ts`（瘦，20 文件）、`authFetchJSON`（15 文件） |
| 裸 fetch | 24 处绕过所有客户端 |
| 状态管理 | authStore 手写 useSyncExternalStore、notification/theme 用 zustand |
| React Query | 全局接入，仅 audit 1 功能用 |
| `usePermission` | 不订阅 store，登录后权限不刷新（活跃缺陷） |
| `useCachedQuery` | React Query 重实现，7 派生 hook 零消费者（死代码） |

### 7.2 方案

1. **收敛单一客户端**：将 `api-client.ts` 能力（token/CSRF/401/retry/错误归一化）合并进 `api/client.ts`；迁移 15 处 `authFetchJSON` + 24 处裸 fetch；删 `api-client.ts`。
2. **服务端状态归 React Query**：24 处裸 fetch 改 `useQuery`/`useMutation`。
3. **修复 `usePermission`**：改为订阅 `authStore`（`const { user } = useAuthStore()`），响应登录态；修正 `authStore.ts:91` 违反自定不变量的 `localStorage` 直读。
4. **删死代码**：`useCachedQuery.ts` 及派生 hook、`hooks/index.ts` 相关 re-export。
5. **目录整理**：`ChatHistorySidebar`/`AIAssistant` 移入 `components/chat/`；合并 `alert/` 与 `alerts/`。

### 7.3 工作量与风险

- **工作量**：1.5-2 人周
- **风险**：低。逐文件验证，Playwright E2E 护航。
- **回滚**：按文件粒度。

---

## 8. P4 — CI 安全门禁化

### 8.1 现状

`.github/workflows/security.yml` 6 个扫描器全 `continue-on-error`/`exit-code: 0`，只报告不阻断。

### 8.2 方案：分级门禁

```yaml
block-on-critical:           # 硬门禁
  - gitleaks detect            # 任何密钥泄漏 → fail
  - trivy --severity CRITICAL --exit-code 1
  - npm audit --audit-level=high
  - bandit -iii
warn-on-high:                 # 软门禁（continue-on-error）
  - pip-audit
  - trivy --severity HIGH
```

**配套**：Trivy 首次运行建基线快照，后续仅对**新增**漏洞门禁（避免历史债阻塞）；PR 模板加勾选项 `[ ] 已确认无新增 HIGH+`。

### 8.3 工作量与风险

- **工作量**：0.5 人日
- **风险**：极低。初期可能暴露一批历史漏洞使 CI 红——先建基线规避。

---

## 9. 里程碑与排期

> 假设 1 后端 + 0.5 前端，P3/P4 并行。P2 默认按路线 A 编排。

| 里程碑 | 时间窗 | 交付物 | 前置 |
|--------|--------|--------|------|
| **M0: P0 验证+修复** | 第 1 周 | 线上验证 → 3 缺陷修复 → `AlertService.analyze` 集成测试通过 | 无 |
| **M1: P4 门禁** | 第 1 周（并行） | CI 分级门禁上线 + 基线 | 无 |
| **M2: P1 第一批** | 第 2-3 周 | `blocked_ips`/`security_alerts` 分层 + websocket_manager 下沉 | M0 |
| **M3: P1 完成** | 第 4-5 周 | 剩余 4 域 + `auth`/`playbook_definitions` 瘦身 | M2 |
| **M0.5: P2 设计评审** | 第 5 周 | 决策 DP-1（A/B 路线） | M3 |
| **M4: P2 执行** | 第 6-8 周 | 路线 A：dispatcher + 入口迁移 | M0.5 |
| **M5: P2 收尾** | 第 8-9 周 | 状态 schema 收敛 + 全量回归 | M4 |
| **M6: P3 前端** | 第 6-7 周（并行） | apiClient 收敛 + RQ 迁移 + 死代码清理 | 无 |
| **M7: 收尾** | 第 10 周 | 全量回归 + 文档 + 度量复盘 | M5, M6 |

**关键路径**：M0 → M2 → M3 → M0.5 → M4 → M5，**约 9 周**（路线 A）。
- 若 DP-1 选路线 B：M4/M5 延伸至第 13 周，关键路径约 **12-13 周**。
- P3/P4 不在关键路径。

---

## 10. 风险与回滚

| 风险 | 概率 | 影响 | 缓解 |
|------|------|------|------|
| P0 未覆盖某调用路径 | 低 | 高 | 集成测试覆盖 AlertService 成功路径（影响面核心） |
| P1 漏改业务逻辑 | 中 | 中 | 逐域 PR + 回归 + 行为等价校验 |
| P2 执行语义偏移 | 中 | 高 | 端到端回归 + feature flag 灰度（路线 B 尤需） |
| P3 破坏 auth 流程 | 低 | 高 | 保留旧 client 直到新 client 全量验证 + E2E |
| P4 门禁阻塞历史债 | 高 | 低 | 先建基线，仅对新增门禁 |
| DP-1 决策延误 | 中 | 中 | M0.5 设硬截止，默认走路线 A |

**回滚**：代码级按 PR revert；P2 feature flag 运行时关闭；整计划在长分支 `chore/architecture-remediation` 推进，不合并即不上线。本次无 schema 变更，无数据回滚。

---

## 11. 验收标准与度量

### 11.1 各阶段 DoD

| 阶段 | 验收标准 |
|------|---------|
| P0 | ① 步骤 0 线上验证完成（确认是否在崩）② 非 analysis AI 任务不再 AttributeError ③ **`AlertService.analyze` 成功路径集成测试通过** ④ 单测覆盖 if/else 两分支 |
| P1 | ① 6 个新 Repository 存在且被使用 ② `grep session.execute routers/` 命中 < 10（从 88 降） ③ `alert_stream_service` 不再 import routers ④ `auth.py` < 80 行 |
| P2 | ① DP-1 已决策 ② `adapter.py` 死代码删除 ③ 路线 A：dispatcher 统一入口；路线 B：`v6_linear/` 删除 ④ 所有 builtin playbook 回归通过 |
| P3 | ① 仅剩 1 个 API 客户端 ② 裸 `fetch()` = 0 ③ `usePermission` 登录后能刷新 ④ RQ 使用功能数 > 5 |
| P4 | ① CRITICAL 漏洞/密钥泄漏 fail CI ② 历史基线已记录 ③ PR 模板勾选项生效 |

### 11.2 度量指标（整改前后对比）

| 指标 | 整改前 | 目标 |
|------|--------|------|
| AI 层运行时 AttributeError | 3 处 | 0 |
| 路由 session 直查处 | 88 | < 10 |
| 缺失 Repository 的域 | 6 | 0 |
| Playbook 活跃路径 | 3（+1 死） | 路线 A：1 dispatcher；路线 B：1 |
| 死代码行数 | ~800 | 0 |
| 前端 API 客户端 | 3 | 1 |
| 前端裸 fetch | 24 | 0 |
| CI 硬门禁扫描器 | 0 | 4 |

---

## 12. 附录 A：v2.0 变更记录

相对 v1.1（批注版）吸收的评审结论：

| # | v1.1 批注 | v2.0 处理 |
|---|----------|----------|
| 评审1 | P0 影响面低估 | §4.1 明确 4 核心服务；P0 DoD 加"AlertService.analyze 成功路径集成测试" |
| 评审2 | P0 缺前置验证 | §4.3 新增"步骤 0：线上验证"，据此决定是否维持 P0 |
| 评审3 | P1 数字 117/21 不准 | 全文更正为 88/17，top1=`security_alerts`=20 |
| 评审4 | AlertSink 是 YAGNI | §5.2.3 改为"下沉 websocket_manager"，删除 AlertSink Protocol；P1 工期 2-3 周→2 周 |
| 评审5 | P2 阶段2 不可行（不同构） | §6 重写为路线 A（推荐，2-3 周）/ 路线 B（5-7 周），新增 M0.5 决策点 |
| 评审6 | dict 可能是逃生口 | 已核实推翻（注释错误，dict 必崩）；P0-3 确认为 bug，处置与 P0-1/P0-2 统一 |

**结构变化**：v2.0 删除了 v1.1 的所有 `📝 评审N` 插桩批注，将结论固化为正文；新增 §3.2 决策点 DP-1、§6.5 前置条件、附录 A。
