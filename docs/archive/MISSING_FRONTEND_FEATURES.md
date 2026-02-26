# 🎯 后端已实现但前端缺少展示的功能

**生成日期**: 2026-02-25
**项目**: SOC Copilot v0.9.0

---

## 📊 概览

本文档列出了后端 API 已实现但前端缺少对应展示页面的功能。

### 统计数据
- ✅ **已有前端页面**: 15 个功能
- ❌ **完全缺失**: 7 个功能
- ⚠️ **需检查完善**: 4 个功能

---

## ❌ 完全缺失的前端页面（优先级高）

### 1. 🤖 AI 模型管理

**后端路由**: `/api/v1/ai-models`
**后端文件**: `backend/routers/ai_models.py`

**API 端点**:
- `GET /api/v1/ai-models` - 列出所有 AI 模型
- `GET /api/v1/ai-models/default` - 获取默认模型
- `POST /api/v1/ai-models/default` - 设置默认模型
- `POST /api/v1/ai-models/test` - 测试模型
- `POST /api/v1/ai-models/refresh` - 刷新模型列表

**建议页面路径**: `/admin/ai-models` 或 `/settings/ai-models`

**核心功能**:
- 查看所有可用的 AI 模型列表（OpenAI, Anthropic, 等）
- 显示每个模型的名称、提供商、状态
- 设置系统默认模型
- 测试模型连接和响应
- 刷新模型列表以获取最新配置
- 查看模型使用统计

---

### 2. 📋 AI 任务队列监控

**后端路由**: `/api/v1/ai-tasks`
**后端文件**: `backend/routers/ai_tasks.py`

**API 端点**:
- `POST /api/v1/ai-tasks` - 创建 AI 任务
- `GET /api/v1/ai-tasks` - 获取任务列表
- `GET /api/v1/ai-tasks/{task_id}` - 获取任务详情
- `POST /api/v1/ai-tasks/{task_id}/cancel` - 取消任务
- `GET /api/v1/ai-tasks/queue/stats` - 队列统计

**建议页面路径**: `/admin/ai-tasks` 或 `/ai-tasks`

**核心功能**:
- 查看所有 AI 任务队列
- 实时任务状态监控（pending, processing, completed, failed）
- 任务详情查看（输入、输出、错误信息）
- 取消运行中的任务
- 队列统计（等待中、运行中、成功、失败）
- 任务历史记录和重试

---

### 3. 📊 系统仪表盘

**后端路由**: `/api/v1/dashboard`
**后端文件**: `backend/routers/system_dashboard.py`

**API 端点**:
- `GET /api/v1/dashboard` - 完整系统仪表盘
- `GET /api/v1/database` - 数据库状态
- `GET /api/v1/redis` - Redis 状态
- `GET /api/v1/resources` - 系统资源
- `GET /api/v1/features` - 功能开关

**建议页面路径**: `/admin/dashboard` 或 `/dashboard`

**核心功能**:
- 系统整体健康状态概览
- 数据库状态监控（连接池、查询性能）
- Redis 状态监控（内存使用、连接数）
- 系统资源使用情况（CPU、内存、磁盘）
- 功能开关管理
- 服务健康检查
- 性能指标可视化

---

### 4. 🚨 告警增强管理

**后端路由**: `/api/v1/alerts/enrichment`
**后端文件**: `backend/routers/alert_enrichment.py`

**API 端点**:
- `POST /api/v1/alerts/enrichment/process/{alert_id}` - 处理单个告警
- `POST /api/v1/alerts/enrichment/process-recent` - 处理最近告警
- `GET /api/v1/alerts/enrichment/stats` - 增强统计

**建议页面路径**: `/alerts/enrichment` 或集成到 `/alerts` 页面

**核心功能**:
- 手动触发告警增强处理
- 查看告警增强统计（已处理、待处理、失败）
- 批量处理最近告警
- 增强结果展示
- 增强错误日志查看

---

### 5. 🎯 IOC 命中查看

**后端路由**: `/api/v1/ioc-hits`
**后端文件**: `backend/routers/ioc_hits.py`

**API 端点**:
- `GET /api/v1/ioc-hits` - IOC 命中列表
- `GET /api/v1/ioc-hits/by-asset/{asset_id}` - 按资产查询
- `GET /api/v1/ioc-hits/by-history/{history_id}` - 按历史查询
- `POST /api/v1/ioc-hits/manual` - 手动添加 IOC 命中

**建议页面路径**: `/threat-intel/ioc-hits` 或 `/ioc-hits`

**核心功能**:
- IOC 命中列表展示
- 按资产筛选 IOC 命中
- 按历史记录查询
- IOC 类型分布（IP, Domain, Hash, URL）
- 命中时间线
- 手动添加 IOC 命中记录
- 导出 IOC 命中报告

---

### 6. 🕒 历史记录管理

**后端路由**: `/api/v1/history`
**后端文件**: `backend/routers/history.py`

**API 端点**:
- `GET /api/v1/history` - 历史记录列表
- `GET /api/v1/history/{history_id}` - 历史详情
- `DELETE /api/v1/history/{history_id}` - 删除历史
- `DELETE /api/v1/history` - 清空历史

**建议页面路径**: `/admin/history` 或 `/history`

**核心功能**:
- 查看所有历史记录列表
- 历史详情查看（输入、输出、元数据）
- 按类型筛选历史记录
- 按时间范围筛选
- 删除单条历史记录
- 批量删除或清空历史
- 历史记录搜索

---

### 7. 🎭 Webhook 管理

**后端路由**: 需确认具体路由
**后端文件**: `backend/routers/webhooks.py`

**API 端点**: 需查看具体实现

**建议页面路径**: `/settings/webhooks` 或 `/integrations/webhooks`

**核心功能**:
- Webhook 配置管理（创建、编辑、删除）
- Webhook 列表展示
- Webhook 日志查看
- 测试 Webhook 发送
- Webhook 事件类型配置
- 重试失败 Webhook
- Webhook 统计（成功、失败率）

---

## ⚠️ 可能实现不完整的页面（需检查）

### 8. 🌐 云原生安全

**前端页面**: `/cloud-native/page.tsx` ✅ 存在
**后端路由**: `/api/v1/cloud-native`
**后端文件**: `backend/routers/cloud_native.py`

**API 端点**:
- `POST /api/v1/cloud-native/containers/scan` - 扫描容器
- `POST /api/v1/cloud-native/kubernetes/scan` - 扫描 K8s
- `GET /api/v1/cloud-native/kubernetes/resources/{type}` - K8s 资源
- `GET /api/v1/cloud-native/cloud/connections` - 云连接
- `GET /api/v1/cloud-native/compliance/report` - 合规报告
- `GET /api/v1/cloud-native/dashboard` - 仪表盘

**需检查功能**:
- [ ] 容器扫描功能是否实现
- [ ] Kubernetes 资源查看是否完整
- [ ] 云连接管理是否可用
- [ ] 合规报告展示是否正确
- [ ] 云原生仪表盘是否展示所有数据

---

### 9. 📢 通知系统

**前端页面**: `/settings/notifications/page.tsx` ✅ 存在
**后端路由**: `/api/v1/notifications`
**后端文件**: `backend/routers/notifications.py`

**API 端点**:
- `POST /api/v1/notifications/test` - 测试通知
- `GET /api/v1/notifications/channels` - 通知渠道状态
- `GET /api/v1/notifications/queue/stats` - 队列统计
- `GET /api/v1/notifications/health` - 通知健康检查

**需检查功能**:
- [ ] 通知渠道状态是否正确显示
- [ ] 队列统计是否实时更新
- [ ] 通知测试功能是否可用
- [ ] 健康检查结果是否展示
- [ ] 通知历史是否查看

---

### 10. 📈 监控页面

**前端页面**: `/monitor/page.tsx` ✅ 存在
**后端路由**: `/api/v1/monitor`
**后端文件**: `backend/routers/monitor.py`

**API 端点**:
- `GET /api/v1/monitor/stream` - 监控流
- `GET /api/v1/monitor/snapshot` - 监控快照
- `GET /api/v1/monitor/history` - 监控历史
- `DELETE /api/v1/monitor/history/cleanup` - 清理历史
- `DELETE /api/v1/monitor/history/clear` - 清空历史

**需检查功能**:
- [ ] 监控流是否实时展示
- [ ] 监控快照是否正确显示
- [ ] 历史记录查看功能是否完整
- [ ] 清理历史功能是否可用
- [ ] 数据可视化是否完善

---

### 11. 📝 报告生成

**前端页面**: `/reports/page.tsx` ✅ 存在
**后端路由**: `/api/generate-report`
**后端文件**: `backend/routers/report.py`

**API 端点**:
- `POST /api/generate-report` - 生成报告

**需检查功能**:
- [ ] 报告生成功能是否实现
- [ ] 报告模板选择是否可用
- [ ] 报告下载功能是否正常
- [ ] 报告预览是否展示
- [ ] 报告历史是否记录

---

## ✅ 已有对应页面的功能

### 12. 🔑 API Keys 管理
**前端页面**: `/settings/api-keys/page.tsx` ✅
**后端路由**: `/api/v1/api-keys`
**状态**: 完整实现

---

### 13. 💼 资产管理
**前端页面**: `/assets/page.tsx` ✅
**后端路由**: `/api/v1/assets`
**状态**: 完整实现

---

### 14. 📤 导出功能
**前端页面**: `/reports/page.tsx` ✅
**后端路由**: `/api/v1/export`
**状态**: 完整实现

---

### 15. 🔐 密钥管理
**前端页面**: `/admin/secrets/page.tsx` ✅
**后端路由**: `/api/v1/secrets`
**状态**: 完整实现

---

### 16. 🎭 剧本管理
**前端页面**: `/playbooks/page.tsx` ✅
**后端路由**: `/api/v1/playbooks`
**状态**: 完整实现

---

### 17. 🛒 Marketplace
**前端页面**: `/marketplace/page.tsx` ✅
**后端路由**: `/api/v1/marketplace`
**状态**: 完整实现

---

### 18. 🎯 威胁狩猎
**前端页面**: `/threat-hunting/page.tsx` ✅
**后端路由**: `/api/v1/threat-hunting`
**状态**: 完整实现

---

### 19. 👤 用户行为分析 (UEBA)
**前端页面**: `/ueba/page.tsx` ✅
**后端路由**: `/api/v1/ueba`
**状态**: 完整实现

---

### 20. 🔗 事件关联
**前端页面**: `/correlation/page.tsx` ✅
**后端路由**: `/api/v1/correlation`
**状态**: 完整实现

---

## 📋 优先级总结

### 🔴 优先级 P0 - 核心管理功能（必需）
1. **📊 系统仪表盘** - 系统管理员必备，监控整个系统健康状态
2. **🤖 AI 模型管理** - AI 功能管理必需，管理所有 AI 模型配置
3. **📋 AI 任务队列** - 监控 AI 处理状态，排查 AI 相关问题

### 🟡 优先级 P1 - 重要功能增强
4. **🎯 IOC 命中查看** - 威胁情报补充，查看 IOC 检测结果
5. **🚨 告警增强管理** - 告警处理增强，手动触发告警分析
6. **🕒 历史记录管理** - 数据审计需求，查看和清理历史数据

### 🟢 优先级 P2 - 可选功能
7. **🎭 Webhook 管理** - 集成管理，管理外部系统 Webhook
8. **完善云原生页面** - 补充缺失的云原生功能
9. **完善通知系统页面** - 补充通知管理功能
10. **完善监控页面** - 优化监控数据展示
11. **完善报告页面** - 补充报告生成功能

---

## 🎯 实施建议

### 第一阶段（1-2周）
实施 P0 优先级功能：
- 系统仪表盘（核心）
- AI 模型管理
- AI 任务队列监控

### 第二阶段（2-3周）
实施 P1 优先级功能：
- IOC 命中查看
- 告警增强管理
- 历史记录管理

### 第三阶段（3-4周）
完善 P2 优先级功能和检查现有页面：
- Webhook 管理
- 完善云原生、通知、监控、报告页面

---

## 📝 注意事项

1. **API 认证**: 所有新页面都需要处理认证和授权
2. **错误处理**: 需要完善的错误处理和用户提示
3. **加载状态**: 需要添加加载状态和骨架屏
4. **响应式设计**: 需要适配移动端和平板
5. **国际化**: 需要支持中英文切换
6. **权限控制**: 需要根据用户角色控制功能访问

---

**报告生成时间**: 2026-02-25
**下次更新时间**: 实施完成后
