# SOC Copilot 优化报告 v2.0

> 基于 Skills 全面扫描生成 - 2026/04/08

## 执行摘要

通过架构、前端性能、安全和测试四个维度的深度扫描，共发现 **122 个优化项**：

| 维度           | CRITICAL | HIGH   | MEDIUM | LOW    | 总计    |
| -------------- | -------- | ------ | ------ | ------ | ------- |
| 架构与可扩展性 | 0        | 7      | 23     | 9      | 39      |
| 前端性能与质量 | 2        | 12     | 10     | 5      | 29      |
| 安全漏洞       | 2        | 3      | 5      | 4      | 14      |
| 测试覆盖率     | 10       | 15     | 12     | 3      | 40      |
| **总计**       | **14**   | **37** | **50** | **21** | **122** |

---

## 一、安全漏洞 (CRITICAL 优先)

### 1.1 硬编码凭证 (CRITICAL)

**文件:** `backend/.env`

```
NVIDIA_API_KEY=nvapi-qFTni6ysv...
ZHIPU_API_KEY=7b575e9642cf...
OTX_API_KEY=7d16366aa30e9c...
JWT_SECRET=6-yj8jtzGaPf33GOuHeLqdnyrWNXByqq8CW6pT_5EPM
SECRET_ENCRYPTION_KEY=94xQFVaBr-BEYwct6T9fohRBdMYWJcbaFyml2ALlh_M=
```

**修复:**

- 立即轮换所有暴露的凭证
- 将 `.env` 添加到 `.gitignore`
- 生产环境使用 secrets manager

### 1.2 SSL 验证禁用 (CRITICAL)

**文件:** `backend/.env:64`

```
WAZUH_VERIFY_SSL=false
```

**修复:** 生产环境启用 SSL 验证，使用合法证书

### 1.3 默认弱密码 (HIGH)

**文件:** `docker-compose.yml:10,49`

```yaml
POSTGRES_PASSWORD: ${DB_PASSWORD:-changeme}
SECRET_KEY: ${SECRET_KEY:-your-secret-key-here}
```

**修复:** 强制使用强密码，移除默认值

### 1.4 XSS 漏洞 (HIGH)

**文件:** `frontend/public/playbook-test.html`, `frontend/public/sse-test.html`

```javascript
statusDiv.innerHTML = `<span ...>...</span>`; // 多处
```

**修复:** 使用 `textContent` 或 DOMPurify 进行 HTML 消毒

### 1.5 WebSocket 监控端点缺少认证 (MEDIUM)

**文件:** `backend/routers/websocket.py:609-736`

```python
@router.get("/ws/stats")  # 无认证
@router.get("/ws/monitoring/metrics")  # 无认证
@router.get("/ws/monitoring/health")  # 无认证
```

**修复:** 添加 `Depends(get_current_user)` 或限制为管理员

### 1.6 CSRF 中间件未启用 (MEDIUM)

**文件:** `backend/main.py`

中间件已定义但未注册。

**修复:** 调用 `setup_csrf_middleware(app)`

---

## 二、架构问题

### 2.1 大文件/God 类 (HIGH)

| 文件                                         | 行数 | 问题                           |
| -------------------------------------------- | ---- | ------------------------------ |
| `backend/playbook_engine/dag/engine.py`      | 931  | DAG 构建、执行、状态管理混合   |
| `backend/routers/playbook_definitions.py`    | 921  | 业务逻辑与内部 API 混合        |
| `backend/routers/websocket.py`               | 751  | ConnectionManager 嵌入路由文件 |
| `frontend/lib/api.ts`                        | 1853 | 所有 API 端点集中在单文件      |
| `frontend/components/ChatHistorySidebar.tsx` | 672  | 侧边栏职责过多                 |

**修复建议:**

- 提取 `ConnectionManager` 到 `services/websocket_manager.py`
- 拆分 `lib/api.ts` 为领域模块 (assets, playbooks, triggers 等)
- 分离内部 API 到 `/routers/internal/`

### 2.2 N+1 查询模式 (HIGH)

**文件:** `backend/services/alerting/alert_lifecycle.py:57-85`

```python
# 分离查询 alert 和 notes
alert = await session.execute(select(AlertModel).where(...))
notes = await session.execute(select(AlertNoteModel).where(...))
```

**修复:** 使用 `selectinload` 或 `joinedload`

### 2.3 缺少数据库索引 (HIGH)

| 表/列                        | 用途           |
| ---------------------------- | -------------- |
| `playbook_runs.status`       | 频繁过滤       |
| `playbook_runs.started_at`   | 排序和孤儿检测 |
| `security_alerts.created_at` | 时间范围查询   |
| `audit_logs.created_at`      | 清理和过滤     |

**修复:** 创建迁移添加索引

### 2.4 同步阻塞事件循环 (HIGH)

**文件:** `backend/main.py:160-171`

```python
result = subprocess.run(
    [sys.executable, "-m", "alembic", ...],
    ...
)
```

**修复:** 使用 `asyncio.to_thread()` 在线程池中运行

### 2.5 无界集合/内存泄漏 (HIGH)

**文件:** `backend/routers/websocket.py:67-68`

```python
self.known_users: dict[str, datetime] = {}  # 永不清理
```

**修复:** 添加 TTL 和定期清理

---

## 三、前端性能

### 3.1 重库同步导入 (CRITICAL)

| 文件                           | 库        | 大小   |
| ------------------------------ | --------- | ------ |
| `components/dag/DAGCanvas.tsx` | reactflow | ~500KB |
| `components/monitor/*.tsx`     | recharts  | ~300KB |

**修复:** 使用 `next/dynamic` + `ssr: false`

```typescript
const DAGCanvas = dynamic(() => import('@/components/dag/DAGCanvas'), {
  ssr: false,
  loading: () => <LoadingSpinner />
});
```

### 3.2 缺少 useMemo/useCallback (HIGH)

| 文件                                            | 问题                    |
| ----------------------------------------------- | ----------------------- |
| `components/Navigation.tsx:64-117`              | 导航数组每次渲染重建    |
| `app/[locale]/admin/dashboard/page.tsx:133-173` | 辅助函数每次渲染重建    |
| `components/tabs/AssetsTab.tsx:67-88`           | `loadAssets` 未 memo 化 |

**修复:**

```typescript
const mainNavItems = useMemo(() => [...], []);
const handleLoadAssets = useCallback(async () => {...}, [deps]);
```

### 3.3 可访问性问题 (HIGH)

| 文件                                        | 问题                |
| ------------------------------------------- | ------------------- |
| `components/ChatHistorySidebar.tsx:198-285` | 按钮缺少 aria-label |
| `app/[locale]/alerts/[id]/page.tsx:428-485` | Tab 缺少键盘导航    |
| 多个搜索输入                                | 缺少关联标签        |

### 3.4 Token 重复获取 (MEDIUM)

`localStorage.getItem("access_token")` 在 15+ 文件中重复调用。

**修复:** 统一使用 `authFetchJSON` 或 auth context

---

## 四、测试覆盖率

### 4.1 关键服务缺少测试 (CRITICAL)

| 服务                      | 状态   |
| ------------------------- | ------ |
| `vector_store.py`         | 无测试 |
| `ueba_service.py`         | 无测试 |
| `cloud_native_service.py` | 无测试 |
| `trigger_service.py`      | 无测试 |

### 4.2 关键路由缺少测试 (CRITICAL)

| 路由              | 状态   |
| ----------------- | ------ |
| `correlation.py`  | 无测试 |
| `webhooks.py`     | 无测试 |
| `alert_stream.py` | 无测试 |

### 4.3 弱断言模式 (HIGH)

**文件:** 多个测试文件

```python
assert response.status_code in [200, 404]  # 接受 404 表示测试无效
assert response.status_code in [200, 404, 405]
```

**修复:** 明确预期状态码

```python
assert response.status_code == 200
```

### 4.4 E2E 硬编码等待 (HIGH)

**文件:** 多个 E2E 文件

```typescript
await page.waitForTimeout(3000); // 不稳定
```

**修复:** 使用 `waitFor()` 断言

```typescript
await expect(page.locator('[data-testid="alert-table"]')).toBeVisible();
```

### 4.5 前端单元测试缺失 (HIGH)

| 目录      | 文件数 | 测试状态 |
| --------- | ------ | -------- |
| `hooks/`  | 9      | 3 有测试 |
| `stores/` | 4      | 0 有测试 |
| `lib/`    | 24+    | 0 有测试 |

---

## 五、优先修复顺序

### P0 - 立即修复 (安全关键)

1. [ ] 轮换所有暴露的 API 密钥和密码
2. [ ] 启用 SSL 验证 (`WAZUH_VERIFY_SSL=true`)
3. [ ] 修复 XSS 漏洞 (innerHTML → textContent)
4. [ ] 添加 `.env` 到 `.gitignore`

### P1 - 本周修复 (高影响)

1. [ ] 提取 WebSocket ConnectionManager
2. [ ] 添加数据库索引
3. [ ] 修复同步 subprocess 阻塞
4. [ ] 动态导入 ReactFlow/Recharts
5. [ ] 添加 useMemo 到 Navigation
6. [ ] 为关键服务添加测试

### P2 - 本月修复 (中等优先级)

1. [ ] 拆分 lib/api.ts
2. [ ] 启用 CSRF 中间件
3. [ ] WebSocket 监控端点添加认证
4. [ ] 添加无界集合清理机制
5. [ ] 修复弱断言模式
6. [ ] E2E 测试使用 waitFor 替代 setTimeout

### P3 - 后续迭代

1. [ ] 添加前端单元测试 (hooks, stores, lib)
2. [ ] 添加可访问性标签
3. [ ] 统一 Token 获取模式
4. [ ] 添加 E2E 视觉回归测试

---

## 六、已完成的优化

### 本次会话完成的优化 (2026/04/08)

#### P0 安全关键修复

- [x] **启用 SSL 验证** - `WAZUH_VERIFY_SSL=true`
- [x] **启用 CSRF 中间件** - 在 main.py 中调用 `setup_csrf_middleware()`
- [x] **修复 XSS 漏洞** - 删除存在漏洞的测试文件 (playbook-test.html, sse-test.html)
- [x] **验证 .gitignore** - .env 文件未被 git 跟踪

#### P1 高优先级修复

- [x] **修复同步 subprocess 阻塞** - 使用 `asyncio.to_thread()` 运行 Alembic 迁移
- [x] **优化 Navigation 组件** - 添加 `useMemo` 和 `useCallback` 减少不必要的重渲染
- [x] **提取 WebSocket ConnectionManager** - 创建 `services/websocket_manager.py`
- [x] **验证数据库索引** - 索引已存在于 v0_9_0 和 v0_9_1 迁移中

#### 之前会话完成的优化

- [x] 清理前端 `any` 类型 (162 → 0)
- [x] 修复审计日志 N+1 查询
- [x] 拆分前端大组件 (useUserModals hook)
- [x] 提取审计日志装饰器
- [x] 修复裸 `except:` 语句
- [x] 修复泛捕获 `except Exception`
- [x] 移除 console.log (P1)
- [x] WebSocket Token 通过 header 传递
- [x] SSRF 防护 (HTTP executor)
- [x] 重定向验证 (login page)

---

## 七、量化指标建议

| 指标                     | 当前 | 目标  |
| ------------------------ | ---- | ----- |
| 后端测试覆盖率           | ~30% | 80%   |
| 前端测试覆盖率           | ~5%  | 60%   |
| TypeScript any           | 0    | 0     |
| 安全漏洞 (CRITICAL/HIGH) | 5    | 0     |
| 大文件 (>800行)          | 5    | 0     |
| E2E 覆盖页面             | 8/20 | 18/20 |

---

_报告生成时间: 2026/04/08_
_扫描工具: Claude Code Skills (架构、前端、安全、测试)_
