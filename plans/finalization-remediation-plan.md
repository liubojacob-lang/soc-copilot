# SOC Copilot 收尾改造实施计划（v1）

> 依据：2026-09-19 系统级完整审计报告（整体完成度 ~78%）
> 目标：消除全部 P0/P1，消化收尾相关 P2，达成收尾标准（Definition of Done），发布 v0.9.4
> 总工作量预估：**10–14 个工作日**（Phase 1–4 为收尾硬性部分，约 8–11 天；Phase 5 明确不做）

---

## 0. 执行约定（适用于所有任务）

| 约定 | 内容 |
|---|---|
| 分支策略 | 从当前 HEAD 拉 `release/0.9.4` 收尾分支；每个任务独立分支 `fix/T1.1-xxx`，合并回 release 分支 |
| 提交规范 | Conventional Commits（`fix:` / `refactor:` / `test:` / `chore:` / `docs:`），一个任务一个或一组提交；**提交动作需用户确认后执行** |
| 仿真同步 | **每个任务代码修改完成并自检通过后，必须立即执行 `./Scripts/sim.sh update`**（AGENTS.md 强制守则），并在仿真环境完成人工验证后才算任务关闭 |
| 测试门槛 | 每个任务：`ruff check` + 相关 pytest 子集全绿；每个 Phase 结束：后端全量 pytest + 前端 `tsc && vitest run && next build` + E2E（Phase 2 起为必须） |
| 回滚方式 | 每任务独立分支 + 独立提交，回滚 = revert 单个 merge commit；涉及 DB 迁移的任务必须提供 downgrade |
| 用户动作项 | 计划中标注 `[USER]` 的步骤（密钥轮换、Xcode 许可、外部账号操作）需要用户本人执行 |

---

## 阶段总览与依赖

```
Phase 0 准备(0.5d)
   │
Phase 1 P0 修复(2–3d) ── T1.1 AI降级 ── T1.2 Trivy ── T1.3 密钥[USER为主]
   │
Phase 2 P1 修复(4–5d)
   ├─ T2.1 dev后门      ├─ T2.5 分诊回流(依赖T1.1)
   ├─ T2.2 建表导出     ├─ T2.6 E2E转正(依赖T2.7)
   ├─ T2.3 约束迁移     ├─ T2.7 前端卫生
   ├─ T2.4 RCA接通      ├─ T2.8 OTX明示
   └─ T2.4b 下线备选    └─ T2.9 cloud-native定性
   │
Phase 3 P2 精简(2–3d) —— 版本对齐 / Prompt接线 / Token统计 / 队列恢复 / 死代码大扫除 / RBAC种子
   │
Phase 4 生产化+发布(1.5–2d) —— Sentry / 备份 / 覆盖率 / v0.9.4 tag
   
Phase 5 = 明确不做清单（见文末）
```

关键顺序约束：
- T1.1 必须先于 T2.5（分诊回流依赖降级语义已修正）
- T2.7 先于 T2.6（E2E 转正前必须保证构建干净，否则首轮 CI 大面积红）
- T2.3 的迁移与 T3.5 的孤立表 drop 迁移**合并为同一迁移批次**（0006–0007），避免迁移链碎片化
- 所有迁移在 sim 的 PostgreSQL 上先行验证（`alembic upgrade head` + `downgrade -1` + `upgrade head`）

---

# Phase 0 — 准备（0.5 天）

## T0.1 修复本机 git 可用性 `[USER]`
- **现状**：审计期间所有 git 命令失败（`You have not agreed to the Xcode license agreements`），项目虽有 `.git` 目录但无法执行任何 git 操作。
- **动作**：用户在终端执行 `sudo xcodebuild -license`（或安装完整 Xcode CLT 后重试）。
- **验证**：`git -C /Users/levent/Desktop/Projects/sec status` 正常返回。
- **为什么排在最前**：没有 git 就没有分支/提交/回滚，后续所有任务的回滚保障都不存在。

## T0.2 建立收尾基线
- **动作**：
  1. `cd frontend && rm -rf node_modules && npm install && npx tsc --noEmit && npm run build` — 记录干净环境构建结果（预期暴露 zustand 幽灵依赖问题，即 T2.7 的证据）。
  2. `cd backend && pytest tests/ -q` — 记录全量测试基线（预期 ~671 用例，覆盖率 ≥47%）。
  3. 记录当前 sim 环境版本与 `alembic current`（应为 `0005_user_2fa_totp`）。
- **产出**：基线记录写入本文档附录（通过/失败清单），作为后续每个 Phase 的对照。

## T0.3 建分支
- `git checkout -b release/0.9.4`，此后所有任务分支从它拉出。

---

# Phase 1 — P0 修复（2–3 天）

## T1.1 清除 AI 降级模式的伪造数据 ⏱ 1 天

**问题**：LLM 失败时 `services/llm_retry.py:87-370` 的 `_build_heuristic_alert_response()` 编造具体"证据"（虚构 DNS 频率"8-12 次/秒"、硬编码熵值 4.2、硬编码涉事域名 `0xcd10e1.tech`、confidence 88-92 分），输出格式与真实分析无异，仅靠 `degraded: true` 标记。SOC 分析师可能据此做出错误处置。

**改动内容**：
1. `backend/services/llm_retry.py`
   - **删除** `_build_heuristic_alert_response()` 整个方法（L87-370）。
   - `_create_degraded_response()`（L372 起）中 alert 模块的分支（L391-396 附近 `heuristic_data = self._build_heuristic_alert_response(...)`）改为统一走**最小降级响应**：仅含 `degraded: true`、`error_reason`、空的分析字段（该方法内已有 report/threat_intel 模块的最小降级先例，L468/L477，照此风格实现）。
   - 保持对外返回结构不变（schema 字段仍在、值为空/None + degraded 标记），避免下游 `alerting/alert_service.py` 落库与前端解析崩溃。
2. `backend/services/ai_service_enhanced.py:646-754`（聊天降级）
   - 保留规则引擎回复，但**响应首段强制追加固定声明**（如 `[Rule-engine mode: AI provider unavailable, this is a deterministic fallback response]`），并在响应体中带 `degraded: true`。
3. 前端降级可视化：
   - 定位告警研判结果的消费组件（`frontend/app/[locale]/alerts/[id]/page.tsx` 及 AI 结果卡片组件），对 `degraded === true` 渲染醒目警告横幅（amber/red，含 i18n 双语文案：`degradedBanner` 新增到 `messages/en.json` 与 `zh-CN.json`）。
   - AI 聊天界面（`hooks/useAIChat.ts` 消费侧）对降级首段声明做样式区分（灰色斜体或标记徽章）。
4. 测试：
   - 更新 `backend/tests/test_llm_retry.py`：新增断言——降级响应中**不含**任何编造字段（dns/entropy/`0xcd10e1.tech`/具体 confidence 数值）；断言 `degraded is True` 且 `error_reason` 非空；断言三模块（alert/report/threat_intel）降级结构一致。
   - 若现有用例断言了启发式行为，如实改写为新的最小降级契约。

**验证**：`pytest tests/test_llm_retry.py`；`./Scripts/sim.sh update` 后，临时把 sim 的 `ZHIPU_API_KEY` 置为无效值 → 触发一次告警分析 → 前端应显示降级横幅而非逼真假分析 → 恢复 Key。

**回滚**：revert 单提交。风险低——降级路径仅在 LLM 故障时走到。

---

## T1.2 Trivy 未安装时禁用 mock 漏洞数据 ⏱ 0.5 天

**问题**：`backend/services/integration/trivy_service.py:229-238`（已实测确认）Trivy 二进制不存在时 `_generate_mock_result(image)` 返回编造 CVE 并**写入缓存**；安全产品展示假扫描结果是正确性事故。

**改动内容**：
1. `trivy_service.py`：`_check_trivy_installed()` 为 False 时不再返回 mock——定义 `TrivyNotInstalledError(Exception)`（携带 message="Trivy scanner is not installed on this host"），删除该分支对 `_generate_mock_result` 的调用；`_generate_mock_result` 方法本身若再无其他调用点则一并删除。
2. 调用方适配：`routers/cloud_native.py` 与 `routers/security_vulnerabilities.py` 中 Trivy 扫描端点捕获 `TrivyNotInstalledError` → 返回 `503`（或 `409`）结构化错误 `{"code": "SCANNER_NOT_INSTALLED", ...}`（沿用现有异常处理器风格）。
3. 前端：cloud-native 页与漏洞页对 `SCANNER_NOT_INSTALLED` 显示"扫描器未安装"空态（i18n 双语），不显示任何漏洞数据。
4. 测试：更新 `backend/tests/test_trivy_service.py`——未安装时断言抛错/503，且**无缓存写入**（`_cache_scan_result` 不被调用）。

**验证**：`pytest tests/test_trivy_service.py`；`./Scripts/sim.sh update` 后在 sim（无 trivy）点扫描按钮 → 应见"扫描器未安装"提示而非漏洞列表。

**回滚**：revert 单提交。

---

## T1.3 密钥治理 ⏱ 1 天（其中大部分为 `[USER]` 动作）

**问题**：根 `.env` 落盘 10+ 个真实 API Key（Anthropic/智谱/OpenAI/NVIDIA/Moonshot/OpenRouter/OTX/AbuseIPDB/飞书/Slack/SMTP）；`.env.security` 含真实 ES/Wazuh 密码；`backups/20260908_000945/env_.env` 是 `.env` 明文副本；CHANGELOG 0.9.2 自认 git 历史含 legacy blobs。

**改动内容**：
1. `[USER]` **立即轮换**上述全部 Key（各供应商控制台操作）。优先级：LLM 六家 + 飞书/Slack webhook（可被打出去）+ SMTP。
2. 代码/脚本侧（代理执行）：
   - 删除 `backups/20260908_000945/env_.env`（先与用户确认备份集中是否还有其他明文凭据文件，一并清理）。
   - `Scripts/backup.sh`：备份范围**排除 `.env*`**（或改为 `gpg --symmetric` 加密后纳入），并在备份 manifest 中记录"secrets excluded by design"；同步检查 k8s backup CronJob 是否会拷贝 env（若会，同样排除）。
   - `.env.security` 处理：确认其服务的 compose（docker-compose.security.yml 引用自建镜像，本身不可用）——内容替换为占位符或将文件移出项目目录 `[USER]` 决定。
3. `[USER]` **git 历史核查与 scrub**：
   - `git log --all --oneline -- .env .env.security` 确认历史泄漏范围；
   - 如确认存在：`git filter-repo --path .env --invert-paths`（重写历史，需协调所有克隆）或最低限度——在 README 安全节记录"历史含已轮换的旧 Key"。
4. `security-modules/log-forwarder/main.py:18-19` 的默认 `changeme`/`verify_certs=False`：改为启动时缺省即报错退出（该模块当前未部署，改动无风险）。

**验证**：`grep -r "sk-\|API_KEY=" backups/` 无明文命中；`.env` 更新为新 Key 后 `./Scripts/sim.sh update` + 调用一次 AI 聊天确认新 Key 生效。

**回滚**：不适用（轮换不可逆，正是目的）。

---

# Phase 2 — P1 修复（4–5 天）

## T2.1 dev 管理员后门加门禁（推荐直接删除）⏱ 0.5 天

**问题**：`backend/services/auth_service.py:102-115`（已实测确认）`ENVIRONMENT=development` 时硬编码密码 `Admin123!`/`Admin123456!` 自动放行并**改写存储哈希**。当前 sim 以 production 运行未激活，但误配部署即失守。

**改动内容（推荐方案：删除）**：
- 删除整个 dev fallback 块（L100-115），密码验证只走 `verify_password()` 一条路径。
- 理由：正规的 `BOOTSTRAP_ADMIN_PASSWORD` 流程已存在且生产有强度校验；需要重置密码时有 `scripts/unlock_user.py` 与强制改密流程。遗留的开发便利不值得留后门。
- 若用户坚持保留开发便利 → 备选方案：新增 `DEV_ALLOW_LEGACY_ADMIN_PASSWORDS`（default `false`），仅当 `environment=development` **且**开关显式为 true 时生效，并在启动日志打 WARNING。
- 测试：`test_auth.py` 新增用例——development 环境下 `Admin123!` 登录被拒（锁定计数正常累加）。

**验证**：`pytest tests/test_auth.py`；`./Scripts/sim.sh update`（sim 是 production 模式，行为不变）+ 本地 dev 模式起服务确认拒绝。

## T2.2 security_vulnerability 模型导出修复 ⏱ 0.25 天

**问题**：`backend/models/__init__.py` 未导入 `security_vulnerability`（已实测确认零引用）→ `init_db()`/create_all 不建 `security_vulnerabilities`/`vulnerability_notes` 两张表，目前靠 router import 顺序副作用建表。

**改动内容**：
1. `models/__init__.py`：加入 `from models.security_vulnerability import SecurityVulnerability, VulnerabilityNote` 并补进 `__all__`。
2. 无需新迁移：Alembic baseline（0001）已含这两张表，此修复只影响 create_all 路径（`seed_demo_data.py`、`lifecycle/database_service.py`）。
3. 测试：新增断言 `Base.metadata.tables` 包含两表名的轻量用例（放入 `test_dependencies_misc.py` 或新文件）。

**验证**：`pytest`；`alembic check`（应无 diff）。

## T2.3 唯一约束与缺失索引迁移 ⏱ 0.5 天

**问题**（均已实测确认）：
- `models/trigger.py:26-28` `idempotency_key` 仅 `index=True` 无 unique → 并发可插重复幂等记录；
- `models/blocked_ip.py` 无 `(value, type)` 唯一约束（先查后插存在竞态）；
- `correlated_events.created_at/updated_at` 无索引（retention 按时间扫全表）；`playbook_approvals.run_id` 无索引（审批轮询场景）。

**改动内容**：
1. `alembic revision -m "0006_unique_constraints_and_indexes"`，迁移逻辑：
   - **先清理存量重复**再建约束：`trigger_invocations` 按 `(trigger_id, idempotency_key)` 保留最新一条删除其余（PG 与 SQLite 各写法或用兼容 SQL）；`blocked_ips` 按 `(value, type)` 同理；
   - `create_unique_constraint` on `trigger_invocations.idempotency_key`（注意该列 nullable——PG 中 NULL 不参与 unique，与现状兼容）、`blocked_ips (value,type)`；
   - `create_index` on `correlated_events.created_at`、`playbook_approvals.run_id`；
   - 编写 downgrade（drop 约束与索引）。
2. 同步修改 `models/trigger.py`、`models/blocked_ip.py`、`models/correlated_event.py`、`models/playbook_approval.py` 的模型定义使 ORM 与迁移一致（`unique=True` / `UniqueConstraint` / `index=True`）。
3. 测试：新增迁移后重复插入断言 `IntegrityError` 的用例（参照 `test_p0_idempotency.py` 风格）。

**验证**：`alembic upgrade head` → `downgrade -1` → `upgrade head` 三段式在 sim PG 上执行；`pytest tests/test_p0_idempotency.py` + 新用例；`./Scripts/sim.sh update`。

## T2.4 RCA 根因分析：接通最小闭环 ⏱ 1.5–2 天（推荐）／或 T2.4b 下线 ⏱ 0.25 天

**问题**：`root_cause_analyses` 表（`models/root_cause_analysis.py`，含 reasoning_steps/evidence_chain/human_verified 反馈字段）+ `prompts/root_cause_analysis.md`（3067 字节 CoT 模板）+ 模型导入全部存在，但 **0 service / 0 router / 0 前端** ——宣传的"根因分析"实际不存在。

**推荐方案 A：接通最小闭环**（RCA 是 SOC Copilot 的差异化卖点，表和 prompt 都是现成的）：
1. 新建 `backend/services/rca_service.py`：
   - `async def analyze_root_cause(alert_id, user) -> RootCauseAnalysis`：
     - 组装上下文：告警本体（security_alerts）+ 关联 IOC（ioc_hits）+ 关联案例备注（alert_notes）+ 关联资产（assets 匹配 IP/hostname）；
     - 加载 `prompts/root_cause_analysis.md` 作为 system prompt（用 `importlib.resources` 或相对路径读取，随包分发）；
     - 走 `ai_service_enhanced.generate_structured()`（schema 注入 + 3 次重试 + **T1.1 修正后的最小降级**）；
     - 结果落库 `root_cause_analyses`（含 confidence/category/reasoning_steps/evidence_chain）；同一告警重复分析生成新版本记录。
   - `async def mark_human_verified(rca_id, verdict, user)`：反馈闭环（human_verified + analyst_verdict 字段已有）。
2. Router：`routers/alert.py` 或独立 `routers/root_cause.py` 加两个端点（均 `get_current_user`）：
   - `POST /api/v1/alerts/{alert_id}/root-cause-analysis`（触发，可同步返回——上下文小；若慢则提交 ai_task）
   - `GET  /api/v1/alerts/{alert_id}/root-cause-analyses`（历史列表）
   - `POST /api/v1/root-cause-analyses/{id}/feedback`（人工验证反馈）
3. Schema：`schemas/` 新增 `RootCauseAnalysisRequest/Response/Feedback`。
4. 前端：`app/[locale]/alerts/[id]/page.tsx` 详情页新增「根因分析」区块——按钮触发、结果卡片（结论 + confidence + 推理步骤折叠列表 + 证据链）、历史记录下拉、👍/👎 反馈按钮；i18n 双语 key。
5. 测试：`tests/test_rca_service.py`——mock LLM 返回结构化结果，断言落库/查询/反馈闭环；降级路径断言最小降级响应。

**备选方案 B：下线**——删除 `models/root_cause_analysis.py` 导入 + `prompts/root_cause_analysis.md` + 出 0007 drop 迁移 + README 移除相关表述。**二选一必须在 Phase 2 结束前定案，不允许继续悬空。**

## T2.5 AI 分诊结果回流告警本体 ⏱ 0.5 天（依赖 T1.1）

**问题**（已实测确认代码）：`services/lifecycle/alert_pipeline_service.py:193-215` 高危告警自动提交 AI 任务，`task_id` 写入 `pipeline_state.ai_task_id`，但任务结果（自由文本）停在 `ai_tasks` 表，**不回写告警**——分诊闭环断裂。

**改动内容**：
1. `services/ai_task_service.py` 任务完成回调处（任务状态翻转为 completed 的位置）：当 `task_type == ALERT_ANALYSIS` 且 `input_data.alert_id` 存在 →
   - 查回告警，将 `result` 摘要写入 `alert.raw_data["pipeline"]["ai_triage"]`（含 summary + completed_at + task_id）；
   - 若结果含可解析的 severity 建议，写入 `pipeline.ai_suggested_severity`；
   - 触发一次 WebSocket 告警更新推送（复用现有 push 通道，若该通道只支持新建告警则降级为不推送，前端靠轮询）。
2. 前端：alerts 列表加「AI 已分诊」徽标（`raw_data.pipeline.ai_triage` 存在时）；详情页显示分诊摘要。
3. 测试：`tests/test_ai_task_service.py` 扩展——任务完成后断言告警 raw_data 被更新。

## T2.6 E2E 转正 + 补 cases spec ⏱ 1 天（依赖 T2.7）

**改动内容**：
1. `.github/workflows/e2e.yml`：`schedule: nightly` 改为 `on: pull_request + push(main/release*)`；job 设为 required（repo 设置里勾选）；首轮先只跑 `auth/alerts/cases/dashboard` 四个 spec（`grep` 过滤），跑绿一个 Phase 后再放开到全部 12 个。
2. `frontend/e2e/global.setup.ts`：健康检查 URL 从硬编码 `:8000` 改为 `process.env.E2E_BACKEND_URL ?? 'http://127.0.0.1:8000'`，workflow 中注入。
3. 新增 `frontend/e2e/cases.spec.ts`：登录 → 创建 case → 关联告警 → 状态流转（open→in_progress→resolved，断言非法流转被拒）→ 添加评论 → 删除（带确认）→ 列表校验。
4. 处理首轮转正暴露的腐化（workflow 文件头注释已预期"数月未跑，首轮会暴露真实腐化"）——如实修复，不为绿而改断言。
5. `e2e/utils/auth.ts` 弱口令 fallback：本地默认改为读 `frontend/.env.e2e`（gitignore），不存在则报错提示；CI 一次性凭据注入不变。

**验证**：本地 `E2E_BACKEND_URL=http://127.0.0.1:18088 npx playwright test cases auth --project=chromium` 全绿；CI 上 PR 触发 E2E 通过。

## T2.7 前端卫生：依赖声明与死代码清理 ⏱ 0.5 天

**改动内容**：
1. **zustand 决断**（先查证再动手）：`grep -rn "from 'zustand'" frontend/stores frontend/app frontend/components` ——
   - 若仅 `authStore.ts`/`notificationStore.ts`（均 0 引用）使用：直接删除这两个文件（及 `authStore.ts.bak`），**不引入 zustand**；
   - 若 `themeStore.ts`（在用）也依赖 zustand：`npm install zustand` 写入 `frontend/package.json` dependencies，同时删除死 store 文件。
2. 删除已确认的死代码：`lib/alertWebSocket.ts`（450 行）+ `lib/wazuhWebSocket.ts` re-export、`components/websocket/MonitoringDashboard.tsx`、`components/websocket/FilterConfig.tsx`、`app/api/monitor/stream/route.ts`、`app/api/proxy/[...path]/route.ts`、`components/common/PlaceholderPage.tsx`。删除前逐个 `grep -rn` 确认 0 引用（含 e2e/测试）。
3. `login/page.tsx:112,116` 两处硬编码中文错误文案 → 抽成 i18n key（`messages/en.json` + `zh-CN.json` 同步，跑 `scripts/check-i18n-keys.mjs`）。
4. 清理 frontend 目录内不应存在的产物：`venv/`、`dev.log`、`dev.pid`、`frontend.pid`、`debug_*.js`、`fix_missing_translations.py`、`.ruff_cache/`、`authStore.ts.bak`、`coverage/`、`playwright-report/`、`test-results/` → 加入 `frontend/.gitignore`（未跟踪的直接删，已跟踪的 `git rm`）。

**验证**：`rm -rf node_modules && npm install && npx tsc --noEmit && npm run build` 干净环境全绿（这是 T0.2 基线失败的对照）；`vitest run`；`./Scripts/sim.sh update` 冒烟。

## T2.8 外部 TI 配置状态明示 ⏱ 0.25 天

**改动内容**：
1. 后端：`routers/threat_intel.py` 的查询端点在 OTX 未配置（`is_enabled()==False`）时，响应体中附 `"provider_status": "unconfigured"`（而非仅空结果）。
2. 前端：`threat-intel/page.tsx` 对该状态渲染「外部威胁情报源未配置」信息横幅（i18n 双语）。
3. `[USER]` 可选：配置真实 OTX Key 到 sim 环境（`Scripts/sim.sh` 预检变量清单里补充 OTX 为可选变量）。

## T2.9 cloud-native 定性冻结 ⏱ 0.25 天

**改动内容**（纯文档+微调，不再投入功能开发）：
1. README「Core Features」中 cloud-native 条目改为明确标注 *"(demo data — connector roadmap)"*；
2. 前端 cloud-native 页确认 Demo 横幅在**所有** tab 生效（审计确认后端 4 端点都带 `simulated: true`，前端横幅若只盖了部分 tab 则补齐）；
3. 导航菜单该项加 "DEMO" 徽标；
4. `FUTURE_BACKLOG.md` 记录"真实 K8s/容器数据源接入"为规划项。

---

# Phase 3 — P2 精简（2–3 天，只做与收尾直接相关项）

## T3.1 版本对齐 + 文档修正 ⏱ 0.5 天

- `docker-compose*.yml` 的 `IMAGE_TAG` 默认值、`k8s/*.yaml` 镜像 tag、`frontend/sentry.*.config.ts` release 默认值（当前 0.8.0）→ 统一 **0.9.4**；
- README：版本徽章 0.9.0→0.9.4；删除 `MANUAL_TEST.md`/`TEST_CASES.md` 两处死链引用（README.md L359-360/L530-531）；
- `docs/13-testing-guide.md`：移除"95.2% 通过率 / coverage-comprehensive"失实徽章，替换为实测覆盖率数字（Phase 4 后回填终值）；
- CHANGELOG 新增 `[0.9.4]` 条目（收尾批次：本计划全部改动汇总，按 Keep a Changelog 分类）。

## T3.2 Prompt Registry 接入运行时（最小版）⏱ 0.5 天

**问题**：`prompt_registry` 表 CRUD 完整但零消费方，生产 prompt 硬编码在 `alerting/alert_service.py:17-56`、`report_service.py:14-22`、`timeline_service.py`。

**改动内容**：
1. 新建 `backend/services/prompt_resolution.py`：`async def resolve_prompt(name: str, builtin: str) -> str` —— 查 `prompt_registry` 中 `(name, environment=当前环境, is_active=True)` 的最新版本，无记录回退内置常量（**读失败不抛错**，保证注册表故障不影响主链路）；
2. 三处 service 的 prompt 常量改为启动/请求时经 `resolve_prompt("alert_analysis"|"report"|"timeline", builtin)` 解析；
3. seed：`scripts/seed_prompt_registry.py` 把三个内置 prompt 写入注册表（dev/staging 两环境，幂等 upsert），加进 Makefile；
4. 测试：注册表插入修改版 prompt → 断言分析请求使用了新 prompt；注册表清空 → 断言回退内置。
5. 顺带删除 `prompts/alert_analysis.py` 中零调用的 `_load_prompt_from_registry()`/`get_analysis_prompt_async()` 死代码。

## T3.3 Token 用量统计（最小版）⏱ 0.5 天

**问题**：`services/ai_providers.py` 全部 Provider 丢弃响应 `usage`（已实测确认文件中零处 "usage" 引用）；`observability/llm_tracing.py:229-239` 的 usage 提取因输入是 str 永不命中。

**改动内容（不动表结构，纯 metrics + 日志）**：
1. `ai_providers.py`：各 Provider 的 `chat_completion()` 返回值从 `str` 改为携带 usage 的轻量结构（或实例属性 `self.last_usage`——**优先改返回值**为 `ChatResult(content, usage)`，调用方约 6 处同步适配）；`stream_chat_completion` 同理在收尾帧携带 usage；
2. `observability/metrics.py` 新增 Counter：`llm_tokens_total{provider, model, direction(prompt|completion)}` 与 `llm_requests_total{provider, model, status}`；
3. `llm_tracing.py` 输入类型修正为新的 ChatResult；
4. `ai_service_enhanced.py` 各调用点埋点（一行 metrics，不改业务逻辑）。
- 成本核算表/配额**不做**（Phase 5）。

## T3.4 AI 任务队列恢复与优先级 ⏱ 0.5 天

**问题**：`services/ai_task_service.py:295-324` 进程内 asyncio.Queue——重启后 pending/processing 任务成僵尸；`priority` 入库但消费端 FIFO 从不排序。

**改动内容**：
1. 启动时恢复：`start_background_processor()` 起始处扫描 `ai_tasks` 中 `status IN (pending, processing)` 且 `updated_at` 超过 timeout 的记录 → pending 的重新入队、processing 的标记 `failed(error_reason="orphaned by restart")`；
2. 消费循环改优先级：队列元素改为 `(priority, seq, task)`，入队 `heapq`（`priority` 越大越先，tie-break 用自增 seq 保证 FIFO 稳定）；
3. 测试：`tests/test_ai_task_service.py` 新增——预置孤儿任务 → 启动处理器 → 断言重新入队/标记失败；高优先级任务先于低优先级被消费。

## T3.5 死代码大扫除（后端）⏱ 0.5–1 天

按「删或接线」二原则处理，每项删除前 `grep -rn` 确认引用为 0：

| 对象 | 处置 | 说明 |
|---|---|---|
| `services/message_broker/kafka_broker.py` | 删 | 全 NotImplementedError 桩，实际走 Redis Streams |
| `services/threat_hunting/sigma_engine.py:379` `_generate_mock_matches` | 删 | 死代码 |
| `services/impact_service.py:147-151` 历史命中启发式"模拟" | 改 | 响应加 `"estimated": true` 标记（数据本身有价值，去"模拟"语义） |
| `middleware/idempotency_middleware.py` | 删 | 未挂载；幂等由服务层 + T2.3 unique 约束承担 |
| `dependencies/authorization.py` + `ResourceAuthorizationMiddleware` | 删 | 零调用的虚假纵深防御；端点级权限已实测到位（保留会误导后续维护者） |
| `models/tenant_mixin.py` + `services/tenant_query.py` | 删 | 多租户正式下线（文档同步），5 张表的 tenant_id 列**保留**（数据无害，为将来留路） |
| `models/event_similarities`（表+模型） | 删 + drop 迁移 0007 | 无生产者；同步删 data_retention 中的清理分支 |
| `models/playbook_nodes`/`playbook_edges`（表+模型） | 删 + drop 迁移 0007 | DAG 存 definition_json（**删前再查一次 playbook 导入/导出代码确认真不用表**） |
| `models/on_call_schedules`（表+模型） | 删 + drop 迁移 0007 | 只读无写永远空表；同步删 escalation_service 引用 |
| RBAC `roles/permissions/role_permissions` 三表 | **种子启用**（见 T3.6） | 不删 |
| backend 根游离 `test_*.py` ×6、`server*.log` ×6、`check_db.py`、`data/app.db`、旧 `migrations/` 目录 | 移入 `tests/`（有效者）或删 | 游离测试永不执行=死代码；日志/残留直接删 |
| `services/playbook_executors/` 中无注册的执行器 | 查证后处置 | 若有零注册执行器一并清理 |
| 根目录 `backend.log/frontend.log/coverage.json/htmlcov/README.png/architecture.html/fix_*.sh` | 删或移 `archive/` | 多数已被 .gitignore 覆盖（未跟踪磁盘垃圾），已跟踪的 `git rm` |

**迁移注意**：0007 drop 迁移必须先确认 sim/生产库中这些表确无有价值数据（`SELECT count(*)`），downgrade 写全（重建表）。

## T3.6 RBAC 三表种子启用 ⏱ 0.5 天

**问题**：`roles/permissions/role_permissions` 无种子无写入，`dependencies/auth.py:402-426` 查库永远 miss 走硬编码 fallback——永久空转。

**改动内容**：
1. `scripts/seed_rbac.py`：以 `dependencies/auth.py:113-176` 的硬编码角色权限映射为**唯一权威来源**，幂等 upsert 三表（admin/analyst/viewer 全量权限对齐硬编码表）；纳入 Makefile 与 CI 数据库初始化。
2. `dependencies/auth.py`：查库命中即用库值（现逻辑已如此），seed 后自然激活；保留 fallback 作为安全网（库空时行为与今天一致，零回归风险）。
3. 测试：seed 后 `check_permission_in_db` 路径命中断言；`test_rbac_matrix.py` 全量回归（应无行为变化）。
4. 管理界面编辑角色权限**不做**（Phase 5）。

## T3.7（可选，测试全绿才做）小修 ⏱ 0.5 天

- 4 处异常透传改脱敏：`routers/security_alerts.py:223`、`routers/system_dashboard.py:1077`、`routers/websocket.py:407,435` → 改为 `logger.exception(...)` + 通用 detail；
- `models/siem_log.py:53` 与 `models/security_alert.py:132` 的 `lazy="selectin"` → `lazy="selectin"` 改 `lazy="raise"`/`"select"` 需逐一排查调用方，**风险较高**——仅当 Phase 3 结束时全量测试绿且有时间预算才做，否则推 Phase 5。

---

# Phase 4 — 生产化与发布（1.5–2 天）

## T4.1 后端 Sentry 接入 ⏱ 0.5 天
- `requirements.txt` 加 `sentry-sdk[fastapi]`；`main.py` 条件初始化（`SENTRY_DSN` 存在才启用，`environment`/`release` 注入，traces_sample_rate 默认 0.05）；
- 与前端共用 DSN（前后端同 release tag `0.9.4`）；
- `[USER]` 注册 Sentry 项目拿 DSN（或决定继续不用，则删除前端三份死配置——二选一，不留"配了但没开"状态）。

## T4.2 备份链路验证 ⏱ 0.25 天
- T1.3 改过的 `backup.sh` 做一次完整演练：`make db-backup` → 校验 SHA256SUMS → `make db-restore FILE=...` 到临时库 → 抽查数据；确认备份**不含**明文 secrets。

## T4.3 覆盖率地板提升 ⏱ 0.5 天
- Phase 1–3 新增测试自然抬升后，将 `backend/pytest.ini` `--cov-fail-under` 47 → **55**（务实目标；60 推 Phase 5）；
- 若不足，优先补 `services/auth_service.py` 降级路径与 `case_service` 状态机用例。

## T4.4 alert-worker 部署验证 ⏱ 0.25 天
- `docker compose -f docker-compose.prod.yml config` 校验；本地起 worker 容器 → 投递一条 Redis Streams 告警消息 → 断言通知发出（Slack webhook 用测试频道）；
- 修复验证中暴露的问题（该 worker 从未被 e2e 验证过）。

## T4.5 prod compose 补齐 ⏱ 0.25 天
- `docker-compose.prod.yml` 补 postgres/redis/nginx 的 `deploy.resources.limits`（对齐基础 compose）；alert-worker 改用预构建镜像 tag（与 backend 同 tag）替代 `build: ./backend` 现场构建。

## T4.6 发布 v0.9.4 ⏱ 0.5 天
1. 全量回归：后端 pytest + 前端 tsc/vitest/build + E2E 全 12 spec（chromium）+ sim 环境人工冒烟（登录→告警→研判→建案→剧本→审批→报告→登出 主链路）；
2. CHANGELOG 0.9.4 定稿；README/docs 更新（cloud-native 标 Demo、多租户移除、RCA 按 T2.4 决断结果更新）；
3. `release.yml` 流水线走一遍（版本一致性检查→lint/test→tag→镜像构建）；
4. `[USER]` 确认后打 tag `v0.9.4` 并合并 release 分支。

---

# Phase 5 — 明确不做（防止无限扩张）

| 项 | 理由 |
|---|---|
| 多租户真正实现 | 单租户部署定位，tenant_id 列保留即可 |
| Kafka / MQ 替换 | Redis Streams 够用 |
| RAG / vector_store | 无场景支撑，T3.5 顺手删除 `vector_store.py` 死代码 |
| 本地 Ollama/vLLM Provider | 数据敏感性需求出现再做 |
| 案例AI摘要、聊天会话持久化 | 增强项非收尾项 |
| 覆盖率 60%+、移动端实测、k8s CD/GitOps、NetworkPolicy/PDB | 收尾后迭代 |
| 5 张表 ISO 时间字符串迁移 DateTime | 触及历史数据，风险>收益，记录到 FUTURE_BACKLOG |
| cloud-native 真实数据源 | 已定性 Demo 冻结（T2.9） |
| Grafana dashboard v1-v6 历史版本清理、前端 React Query 统一改造 | 纯重构，无功能收益 |

---

# 工作量汇总

| Phase | 内容 | 工作日 |
|---|---|---|
| Phase 0 | 准备与基线 | 0.5 |
| Phase 1 | P0×3（AI伪造/Trivy mock/密钥） | 2–3 |
| Phase 2 | P1×9（含 RCA 1.5–2 天大头） | 4–5 |
| Phase 3 | P2 精简 8 项 | 2–3 |
| Phase 4 | 生产化+发布 | 1.5–2 |
| **合计** | | **10–13.5** |

# 每阶段验收门（DoD）

- **Phase 1**：黑盒可演示——错误 LLM Key 下系统显示明确降级横幅（无逼真假数据）；无 trivy 主机上扫描按钮返回"未安装"；`grep -r API_KEY backups/` 零命中。
- **Phase 2**：`Admin123!` 在任何环境被拒；干净环境前端构建全绿；E2E 四核心 spec 在 CI required 且绿；RCA 要么可点击出结果、要么代码里查无此项。
- **Phase 3**：全库 grep `mock|fake|simulated` 仅剩 cloud-native（明示 Demo）；`alembic check` 无 diff；版本三处一致 0.9.4。
- **Phase 4**：全量回归绿 + 主链路人工冒烟通过 + tag v0.9.4 发布。

# 主要风险与应急

| 风险 | 缓解 |
|---|---|
| T1.1 改降级结构导致前端解析崩溃 | 保持响应 schema 字段不删只置空；alerts 详情页手测；e2e alerts spec 回归 |
| T2.3/T3.5 迁移在存量数据上失败 | 先 count 后清理再约束的三段迁移；downgrade 全写；sim PG 先行演练 |
| T2.4 RCA 改动面最大 | 独立分支独立 PR；schema 走 generate_structured 重试机制；超 2 天预算立即切 T2.4b 下线方案 |
| T2.6 E2E 首轮大面积红 | 按 spec 逐个放开的渐进策略；修复原则=修产品代码而非放宽断言 |
| git filter-repo 重写历史影响所有克隆 | 仅在确认历史确有 Key 后执行，执行前广播+备份 bare 仓库 |
| Xcode 许可修复后 git 状态未知 | T0.1 后先 `git status` 审计意外改动，必要时 stash，再建分支 |
