# SOC Copilot 可优化项清单

本文档汇总项目在代码质量、安全、性能、测试与可维护性等方面的可优化点，便于按优先级逐步改进。

---

## 一、已完成的优化（按优先级实施）

### P0 功能/正确性

- **编辑页保存接口**：已改为 `PATCH /api/playbook-definitions/{id}`，body 为 `{ dag: { nodes, edges } }`，编辑页使用 `api_v7.updateDefinition`。
- **统一定义类 API**：前端 `api_v7` 与主 `api` 中与定义、执行、runs 相关的接口已统一为 `/api/playbook-definitions`（列表、获取、创建、更新、删除、run、runs/{id}、runs/{id}/nodes、cancel）。`getPlaybookDefinition` 也改为请求 playbook-definitions，并兼容返回中的 `dag`/`definition_json`。

### P1 安全

- **生产环境配置校验**：新增 `ENVIRONMENT`、`CORS_ORIGINS`、`STRICT_PRODUCTION_CHECKS`。当 `ENVIRONMENT=production` 时启动会校验 JWT_SECRET、BOOTSTRAP_ADMIN_PASSWORD（及可选 SECRET_ENCRYPTION_KEY）；若 `STRICT_PRODUCTION_CHECKS=true` 则校验不通过会拒绝启动。
- **CORS 可配置**：通过 `CORS_ORIGINS`（逗号分隔）配置允许来源，未配置时默认 `["*"]`，并启用 `allow_credentials=True`。
- **密钥未配置**：SecretService 在密钥未配置时抛 ValueError；DAG 执行时加载 secrets 失败会静默返回空 dict，不中断执行。

### P1 功能

- **Run 取消**：`/api/playbook-definitions/runs/{run_id}/cancel` 会查找当前正在执行的 scheduler 并调用 `scheduler.cancel()`，使执行循环与节点检查 `cancelled` 后退出，并将 run 状态更新为 `cancelled`。
- **审批发起人**：DAGScheduler 接收 `created_by_user_id` 并传入 `NodeExecutionContext.context`；人工审批节点使用 `context.context.get("created_by_user_id")` 写入 `requested_by_user_id`。
- **DAG 执行时加载 secrets**：在 `playbook_dag_scheduler` 中新增 `_load_secrets()`，从 SecretRepository 列出密钥并经 SecretService 解密后传入节点上下文，供 `{{secret.xxx}}` 等使用。

---

## 二、API 与前后端一致性

### 2.1 双路由并存

- 后端存在两套与 Playbook 定义相关的路由：
  - **`/api/playbook-definitions`**（`routers/playbook_definitions.py`）：完整 CRUD，含 PATCH、run、queue-stats 等。
  - **`/api/playbook/definitions`**（`routers/playbook.py`）：部分能力（GET/POST、run、publish、versions、restore、export、import），**无 PATCH**。
- **建议**：在文档或代码中明确“定义 CRUD 与执行”以 `playbook-definitions` 为准；前端 `lib/api.ts` 中与定义相关的接口逐步统一为 `/api/playbook-definitions`，避免混用导致 404/405。

### 2.2 前端 API 调用方式

- 部分页面直接用 `fetch('/api/...')`，部分用 `lib/api.ts` 或 `authFetchJSON`，错误处理与鉴权不统一。
- **建议**：新增或修改接口时优先通过 `api.ts` 或统一封装的 `authFetchJSON` 调用，便于鉴权、错误处理和后续替换 base URL。

---

## 三、后端未完成逻辑（TODO）

以下为代码中标注的 TODO，建议按需实现或收敛行为：

| 位置                                                       | 内容                                                        | 建议                                                                  |
| ---------------------------------------------------------- | ----------------------------------------------------------- | --------------------------------------------------------------------- |
| `services/playbook_dag_scheduler.py`                       | `secrets={},  # TODO: Load secrets`                         | 从 Secret 服务加载密钥并传入节点执行上下文，以支持 `{{secret.xxx}}`。 |
| `routers/playbook_definitions.py`                          | `# TODO: Implement actual cancellation`                     | 实现 run 取消：置位取消标志，调度器/执行器检查后中止后续节点。        |
| `playbook_engine/v7_dag/plugins/builtin_human_approval.py` | `requested_by_user_id=None,  # TODO: Get from auth context` | 从请求/认证上下文写入发起审批的用户 ID。                              |
| `services/playbook_executors/human_approval_executor.py`   | `# TODO: Get from proper context`                           | 同上，从执行上下文或 request state 获取当前用户。                     |
| `services/playbook_executors/ti_lookup_otx_executor.py`    | `# TODO: Call actual OTX service`                           | 若该 executor 仍在使用，应接入真实 OTX 查询逻辑，否则标注为废弃。     |

---

## 四、安全与配置

### 4.1 默认配置

- `core/config.py` 中：
  - `jwt_secret` 默认 `"CHANGE_THIS_IN_PRODUCTION_..."`。
  - `bootstrap_admin_password` 默认 `"admin123!"`。
  - `secret_encryption_key` 默认空字符串。
- **建议**：
  - 生产环境通过环境变量覆盖，且启动时校验：若为默认值或空则拒绝启动或仅允许明确声明的“开发模式”。
  - 首次部署后强制修改 bootstrap 密码，并在文档中说明。

### 4.2 密钥与敏感配置

- 若 `SECRET_ENCRYPTION_KEY` 未配置，密钥管理功能应明确降级或禁用，避免静默失败。
- **建议**：在 `secret_service` 或相关路由中检查 key 状态，未配置时返回明确错误或只读模式。

### 4.3 CORS 与生产

- 当前 CORS 允许 `allow_origins=["*"]`，适合开发。
- **建议**：生产环境改为具体前端域名列表，并限制 `allow_headers`/`allow_methods`。

---

## 五、限流与防护

- 除威胁情报侧有 `rate_limit` 相关逻辑外，API 层未见统一限流（如登录、分析、执行等）。
- **建议**：对 `/api/auth/login`、`/api/analyze-alert`、`/api/playbook-definitions/{id}/run` 等敏感或耗时接口做限流（按 IP 或用户），可考虑 slowapi 或 Nginx/网关层限流。

---

## 六、测试

### 6.1 覆盖范围

- `backend/tests/` 下仅有 `test_v0.7_dag.py` 和脚本 `v0.7_dag_tests.sh`，整体覆盖率有限。
- **建议**：
  - 为核心服务补充单元测试：如 `AlertService`、`DAGCompiler`、`DAGScheduler`、Secret 服务等。
  - 为关键路由补充集成测试：登录、定义 CRUD、run（dry_run）、审批、触发器。
  - 考虑用 pytest + pytest-asyncio，并加入 coverage 与 CI。

### 6.2 测试数据与环境

- 测试若依赖真实 LLM/OTX，可考虑 mock 或使用测试专用配置，避免对外部服务强依赖。

---

## 七、前端与体验

### 7.1 错误与加载状态

- 编辑页保存失败时已改为解析后端 `detail` 并抛出，可进一步在 UI 上区分网络错误、401/403、422 校验错误等，给出明确提示。
- **建议**：关键操作（保存、执行、发布）统一 toast 或内联错误展示，并保留“重试”入口。

### 7.2 编辑页加载定义

- 当前 `getPlaybookDefinition` 使用 `/api/playbook/definitions/${id}`（play 路由），返回中含 `definition_json`；而 `playbook-definitions` 返回 `dag`（即 dag_json）。若后续统一走 `playbook-definitions`，需保证列表/详情/编辑三者数据结构一致（例如统一用 `dag` 或统一用 `definition_json` 并在前端做一层映射）。

### 7.3 类型与可维护性

- 编辑页中 `(node.data as any)`、`(edge as any)` 等可逐步替换为明确的类型（如扩展 React Flow 的 `Node<NodeData>`），便于后续维护和重构。

---

## 八、代理与请求体

### 8.1 PATCH 空 body

- `frontend/app/api/proxy/[...path]/route.ts` 中 PATCH 使用 `await request.json()`，若客户端发送 PATCH 且无 body，可能抛错。
- **建议**：对 PATCH/PUT/POST 先判断 `request.body` 或 content-length，再决定是否 `request.json()`，或使用 `request.json().catch(() => ({}))` 等安全回退。

### 8.2 代理与 Next 重写

- 项目同时存在 Next 的 `rewrites`（`/api/:path*` -> 后端）和 `app/api/proxy/[...path]`。若前端既有 `/api/xxx` 也有通过 proxy 的调用，需确认实际请求路径与后端路由一致，避免重复或冲突。

---

## 九、运维与可观测性

- **建议**：
  - 为长时间运行任务（如 playbook run）增加请求级 trace_id，并写入日志与审计，便于排查。
  - 健康检查 `/api/health` 可增加依赖状态（DB 可连、队列状态、密钥服务是否可用等），便于 K8s/负载均衡探测。
  - 敏感操作（如 apply 执行、密钥更新、用户删除）在审计日志中保留必要上下文（用户、资源 ID、结果）。

---

## 十、文档与规范

- **建议**：
  - 在 README 或 CONTRIBUTING 中说明“定义类 API 以 `/api/playbook-definitions` 为准”，并标注与 `/api/playbook/definitions` 的差异与迁移建议。
  - 环境变量在 `.env.example` 中列全并附简短说明，与 `core/config.py` 保持同步。
  - 对 Playbook 节点类型、变量系统（context/input/secret）、版本与发布流程做简短用户向文档，便于运营与排错。

---

## 优先级建议

| 优先级 | 类别        | 项                                                                        |
| ------ | ----------- | ------------------------------------------------------------------------- |
| P0     | 功能/正确性 | 编辑页保存已修复；统一定义类 API 路径与 body，避免再次 404/405。          |
| P1     | 安全        | 生产环境 JWT/密钥/bootstrap 密码校验；CORS 收紧；密钥未配置时的明确行为。 |
| P1     | 功能        | Run 取消、审批/执行上下文中的用户 ID、DAG 执行时加载 secrets。            |
| P2     | 测试        | 核心服务与关键 API 的单元/集成测试与 CI。                                 |
| P2     | 体验        | 错误提示与加载状态；PATCH 空 body 处理。                                  |
| P3     | 运维        | 健康检查增强、trace_id、限流。                                            |

以上内容会随代码变更而更新，建议与版本发布或迭代计划一起回顾。
