# 后端已实现但前端未集成的功能模块分析报告

**生成日期**: 2026-02-25  
**项目**: SOC Copilot v0.9.0  
**分析范围**: 后端API路由 vs 前端页面组件

---

## 📊 概览统计

| 类别 | 数量 |
|------|------|
| 后端API路由模块 | 37 个 |
| 前端页面模块 | 28 个 |
| ✅ 完整集成 | 21 个 |
| ❌ 完全缺失 | 9 个 |
| ⚠️ 部分实现 | 7 个 |

---

## ❌ 完全缺失的前端页面（优先级 P0-P1）

### 1. 🤖 AI 模型管理 (P0)

**后端路由**: [`/api/ai/models`](backend/routers/ai_models.py:30)  
**前端状态**: ❌ 完全缺失

**API 端点**:
| 方法 | 端点 | 功能 |
|------|------|------|
| GET | `/api/ai/models` | 列出所有 AI 模型 |
| GET | `/api/ai/models/default` | 获取默认模型 |
| POST | `/api/ai/models/default` | 设置默认模型 |
| POST | `/api/ai/models/test` | 测试模型连接 |
| POST | `/api/ai/models/refresh` | 刷新模型列表 |

**建议页面路径**: `/admin/ai-models` 或 `/settings/ai-models`

**核心功能需求**:
- 查看所有可用的 AI 模型列表（OpenAI, Anthropic, 本地模型等）
- 显示每个模型的名称、提供商、状态、能力
- 设置系统默认模型
- 测试模型连接和响应延迟
- 刷新模型列表以获取最新配置
- 查看模型使用统计

---

### 2. 📋 AI 任务队列监控 (P0)

**后端路由**: [`/ai-tasks`](backend/routers/ai_tasks.py:19)  
**前端状态**: ❌ 完全缺失

**API 端点**:
| 方法 | 端点 | 功能 |
|------|------|------|
| POST | `/ai-tasks/submit` | 提交 AI 任务 |
| GET | `/ai-tasks` | 获取任务列表 |
| GET | `/ai-tasks/{task_id}` | 获取任务详情 |
| POST | `/ai-tasks/{task_id}/cancel` | 取消任务 |
| GET | `/ai-tasks/queue/stats` | 队列统计 |

**建议页面路径**: `/admin/ai-tasks` 或 `/ai-tasks`

**核心功能需求**:
- 查看所有 AI 任务队列状态
- 实时任务状态监控（pending, processing, completed, failed）
- 任务详情查看（输入、输出、错误信息）
- 取消运行中的任务
- 队列统计（等待中、运行中、成功、失败数量）
- 任务历史记录和重试功能

---

### 3. 📊 系统仪表盘 (P0)

**后端路由**: [`/api/system`](backend/routers/system_dashboard.py:32)  
**前端状态**: ❌ 完全缺失（与 `/admin/health` 不同）

**API 端点**:
| 方法 | 端点 | 功能 |
|------|------|------|
| GET | `/api/system/dashboard` | 完整系统仪表盘 |
| GET | `/api/system/database` | 数据库状态 |
| GET | `/api/system/redis` | Redis 状态 |
| GET | `/api/system/resources` | 系统资源 |
| GET | `/api/system/ai-models` | AI 模型状态 |

**建议页面路径**: `/admin/system-dashboard` 或 `/dashboard`

**核心功能需求**:
- 系统整体健康状态概览
- 数据库连接池状态监控
- Redis 连接池状态监控
- 系统资源使用情况（CPU、内存、磁盘）
- AI 模型可用性状态
- 服务健康检查
- 性能指标可视化

---

### 4. 🚨 告警增强管理 (P1)

**后端路由**: [`/api/v1/alert-enrichment`](backend/routers/alert_enrichment.py:15)  
**前端状态**: ❌ 完全缺失

**API 端点**:
| 方法 | 端点 | 功能 |
|------|------|------|
| POST | `/api/v1/alert-enrichment/process/{alert_id}` | 处理单个告警 |
| POST | `/api/v1/alert-enrichment/process-recent` | 处理最近告警 |
| GET | `/api/v1/alert-enrichment/stats` | 增强统计 |

**建议页面路径**: `/alerts/enrichment` 或集成到 `/alerts` 页面

**核心功能需求**:
- 手动触发告警增强处理
- 查看告警增强统计（已处理、待处理、失败）
- 批量处理最近告警
- 增强结果展示
- 威胁情报关联展示

---

### 5. 🎯 IOC 命中查看 (P1)

**后端路由**: [`/api/ioc-hits`](backend/routers/ioc_hits.py)  
**前端状态**: ❌ 完全缺失

**API 端点**:
| 方法 | 端点 | 功能 |
|------|------|------|
| GET | `/api/ioc-hits` | IOC 命中列表 |
| GET | `/api/ioc-hits/by-asset/{asset_id}` | 按资产查询 |
| GET | `/api/ioc-hits/by-history/{history_id}` | 按历史查询 |
| POST | `/api/ioc-hits/manual` | 手动添加 IOC 命中 |

**建议页面路径**: `/threat-intel/ioc-hits` 或 `/ioc-hits`

**核心功能需求**:
- IOC 命中列表展示
- 按资产筛选 IOC 命中
- 按历史记录查询
- IOC 类型分布（IP, Domain, Hash, URL）
- 命中时间线
- 手动添加 IOC 命中记录

---

### 6. 🕒 历史记录管理 (P1)

**后端路由**: [`/api/history`](backend/routers/history.py)  
**前端状态**: ❌ 完全缺失

**API 端点**:
| 方法 | 端点 | 功能 |
|------|------|------|
| GET | `/api/history` | 历史记录列表 |
| GET | `/api/history/{history_id}` | 历史详情 |
| DELETE | `/api/history/{history_id}` | 删除历史 |
| DELETE | `/api/history` | 清空历史 |

**建议页面路径**: `/admin/history` 或 `/history`

**核心功能需求**:
- 查看所有历史记录列表
- 历史详情查看（输入、输出、元数据）
- 按类型筛选历史记录
- 按时间范围筛选
- 删除单条历史记录
- 批量删除或清空历史

---

### 7. 🎭 Webhook 管理页面 (P2)

**后端路由**: [`/api/webhooks`](backend/routers/webhooks.py)  
**前端状态**: ❌ 完全缺失（触发器页面存在但功能不同）

**API 端点**: 需查看具体实现

**建议页面路径**: `/settings/webhooks` 或 `/integrations/webhooks`

**核心功能需求**:
- Webhook 配置管理（创建、编辑、删除）
- Webhook 列表展示
- Webhook 日志查看
- 测试 Webhook 发送
- Webhook 事件类型配置

---

### 8. 📤 数据导出功能 (P2)

**后端路由**: [`/export`](backend/routers/export.py:26)  
**前端状态**: ❌ 完全缺失

**API 端点**:
| 方法 | 端点 | 功能 |
|------|------|------|
| GET | `/export/audit-logs` | 导出审计日志 |
| GET | `/export/alerts` | 导出告警数据 |
| GET | `/export/history` | 导出历史记录 |

**建议**: 集成到各相关页面

**核心功能需求**:
- 支持多种导出格式（JSON, CSV, XLSX）
- 审计日志导出
- 告警数据导出
- 历史记录导出
- 自定义导出范围

---

### 9. 🔌 WebSocket 实时告警 (P2)

**后端路由**: [`/ws`](backend/routers/websocket.py:23)  
**前端状态**: ⚠️ 部分实现（AlertWebSocket 组件存在）

**API 端点**:
| 方法 | 端点 | 功能 |
|------|------|------|
| WS | `/ws/alerts` | 实时告警推送 |
| WS | `/ws/playbook-runs` | 剧本运行状态 |

**需检查**:
- WebSocket 连接状态显示
- 断线重连机制
- 多频道订阅管理

---

## ⚠️ 部分实现/需检查完善的功能

### 10. 🌐 云原生安全

**前端页面**: [`/cloud-native/page.tsx`](frontend/app/[locale]/cloud-native/page.tsx) ✅ 存在  
**后端路由**: [`/api/cloud-native`](backend/routers/cloud_native.py:22)

**需检查功能**:
- [ ] 容器镜像扫描功能是否完整
- [ ] Kubernetes 资源查看是否完整
- [ ] 云连接管理是否可用
- [ ] 合规报告展示是否正确

---

### 11. 📢 通知系统

**前端页面**: [`/settings/notifications/page.tsx`](frontend/app/[locale]/settings/notifications/page.tsx) ✅ 存在  
**后端路由**: [`/api/v1/notifications`](backend/routers/notifications.py:21)

**需检查功能**:
- [ ] 通知渠道状态是否正确显示
- [ ] 队列统计是否实时更新
- [ ] 通知测试功能是否可用

---

### 12. 📈 监控页面

**前端页面**: [`/monitor/page.tsx`](frontend/app/[locale]/monitor/page.tsx) ✅ 存在  
**后端路由**: [`/api/monitor`](backend/routers/monitor.py:28)

**需检查功能**:
- [ ] SSE 实时监控流是否正常
- [ ] 监控历史数据查看
- [ ] 历史清理功能

---

### 13. 📝 报告生成

**前端页面**: [`/reports/page.tsx`](frontend/app/[locale]/reports/page.tsx) ✅ 存在  
**后端路由**: [`/api/generate-report`](backend/routers/report.py)

**需检查功能**:
- [ ] 报告生成功能是否完整
- [ ] 报告模板选择
- [ ] 报告下载功能

---

### 14. 🔗 事件关联

**前端页面**: [`/correlation/page.tsx`](frontend/app/[locale]/correlation/page.tsx) ✅ 存在  
**后端路由**: [`/api/correlation`](backend/routers/correlation.py:20)

**需检查功能**:
- [ ] 关联规则管理
- [ ] 关联事件展示
- [ ] 规则引擎评估

---

### 15. 🛡️ Wazuh 集成

**前端页面**: [`/wazuh/page.tsx`](frontend/app/[locale]/wazuh/page.tsx) ✅ 存在  
**后端路由**: [`/api/v1/wazuh`](backend/routers/wazuh_integration.py:20)

**需检查功能**:
- [ ] Wazuh 健康检查
- [ ] Agent 列表展示
- [ ] 告警同步状态

---

### 16. 🔍 威胁情报

**前端页面**: [`/threat-intel/page.tsx`](frontend/app/[locale]/threat-intel/page.tsx) ✅ 存在  
**后端路由**: [`/api/ti`](backend/routers/threat_intel.py)

**需检查功能**:
- [ ] OTX 查询功能
- [ ] 威胁情报统计
- [ ] 缓存状态

---

## ✅ 已完整集成的功能

| 功能 | 前端页面 | 后端路由 | 状态 |
|------|----------|----------|------|
| 用户管理 | `/admin/users` | `/api/v1/users` | ✅ |
| API Keys | `/settings/api-keys` | `/api/v1/api-keys` | ✅ |
| 审计日志 | `/audit` | `/api/v1/audit` | ✅ |
| 资产管理 | `/assets` | `/api/v1/assets` | ✅ |
| 密钥管理 | `/admin/secrets` | `/api/v1/secrets` | ✅ |
| 剧本管理 | `/playbooks` | `/api/v1/playbooks` | ✅ |
| 触发器 | `/triggers` | `/api/v1/triggers` | ✅ |
| Marketplace | `/marketplace` | `/api/marketplace` | ✅ |
| 威胁狩猎 | `/threat-hunting` | `/api/threat-hunting` | ✅ |
| UEBA | `/ueba` | `/api/ueba` | ✅ |
| Dify 集成 | `/dify` | `/api/dify` | ✅ |
| AI 助手 | `/ai-assistant` | `/api/ai` | ✅ |
| 告警列表 | `/alerts` | `/api/v1/security-alerts` | ✅ |
| 告警详情 | `/alerts/[id]` | `/api/v1/security-alerts/{id}` | ✅ |
| 健康检查 | `/admin/health` | `/health` | ✅ |
| 系统设置 | `/admin/settings` | `/api/admin/settings` | ✅ |
| 登录认证 | `/login` | `/api/auth` | ✅ |
| 首页 | `/` | `/api/health` | ✅ |
| 威胁情报仪表板 | `/threat-intel/dashboard` | `/api/ti` | ✅ |

---

## 📋 优先级总结

### 🔴 P0 - 核心管理功能（必需，1-2周内完成）

| 序号 | 功能 | 原因 |
|------|------|------|
| 1 | 📊 系统仪表盘 | 系统管理员必备，监控整个系统健康状态 |
| 2 | 🤖 AI 模型管理 | AI 功能管理必需，管理所有 AI 模型配置 |
| 3 | 📋 AI 任务队列 | 监控 AI 处理状态，排查 AI 相关问题 |

### 🟡 P1 - 重要功能增强（2-3周内完成）

| 序号 | 功能 | 原因 |
|------|------|------|
| 4 | 🎯 IOC 命中查看 | 威胁情报补充，查看 IOC 检测结果 |
| 5 | 🚨 告警增强管理 | 告警处理增强，手动触发告警分析 |
| 6 | 🕒 历史记录管理 | 数据审计需求，查看和清理历史数据 |

### 🟢 P2 - 可选功能（3-4周内完成）

| 序号 | 功能 | 原因 |
|------|------|------|
| 7 | 🎭 Webhook 管理 | 集成管理，管理外部系统 Webhook |
| 8 | 📤 数据导出 | 数据导出需求 |
| 9 | 🔌 WebSocket 完善 | 实时功能增强 |

---

## 🎯 实施建议

### 第一阶段（1-2周）
实施 P0 优先级功能：
1. **系统仪表盘** - 创建 `/admin/system-dashboard` 页面
2. **AI 模型管理** - 创建 `/admin/ai-models` 页面
3. **AI 任务队列监控** - 创建 `/admin/ai-tasks` 页面

### 第二阶段（2-3周）
实施 P1 优先级功能：
1. **IOC 命中查看** - 创建 `/threat-intel/ioc-hits` 页面
2. **告警增强管理** - 集成到 `/alerts` 页面
3. **历史记录管理** - 创建 `/admin/history` 页面

### 第三阶段（3-4周）
完善 P2 优先级功能和检查现有页面：
1. **Webhook 管理** - 创建 `/settings/webhooks` 页面
2. **数据导出** - 集成到各相关页面
3. **WebSocket 完善** - 增强实时功能
4. 检查完善云原生、通知、监控、报告页面

---

## 📝 技术注意事项

1. **API 认证**: 所有新页面都需要处理认证和授权
2. **错误处理**: 需要完善的错误处理和用户提示
3. **加载状态**: 需要添加加载状态和骨架屏
4. **响应式设计**: 需要适配移动端和平板
5. **国际化**: 需要支持中英文切换（使用 next-intl）
6. **权限控制**: 需要根据用户角色控制功能访问

---

## 📁 相关文件参考

### 后端路由文件
- [`backend/main.py`](backend/main.py) - 主应用入口
- [`backend/routers/__init__.py`](backend/routers/__init__.py) - 路由模块导出
- [`backend/routers/ai_models.py`](backend/routers/ai_models.py) - AI 模型管理
- [`backend/routers/ai_tasks.py`](backend/routers/ai_tasks.py) - AI 任务队列
- [`backend/routers/system_dashboard.py`](backend/routers/system_dashboard.py) - 系统仪表盘
- [`backend/routers/alert_enrichment.py`](backend/routers/alert_enrichment.py) - 告警增强
- [`backend/routers/ioc_hits.py`](backend/routers/ioc_hits.py) - IOC 命中
- [`backend/routers/history.py`](backend/routers/history.py) - 历史记录

### 前端 API 文件
- [`frontend/lib/api.ts`](frontend/lib/api.ts) - 主要 API 客户端

### 前端页面目录
- [`frontend/app/[locale]/`](frontend/app/[locale]/) - 页面组件目录

---

**报告生成时间**: 2026-02-25  
**下次更新时间**: 实施完成后
