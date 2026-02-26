# SOC Copilot 项目功能总结

> **文档版本**: v0.8.0  
> **最后更新**: 2026-02-11  
> **项目经理**: AI Assistant  

---

## 📋 项目概述

**SOC Copilot** 是一个面向安全运营中心 (SOC) 的智能工作平台，集成了 AI 驱动的告警分析、自动化响应 Playbook、威胁情报和高级分析功能。

### 技术架构

| 组件 | 技术栈 | 版本 |
|------|--------|------|
| **后端 API** | Python + FastAPI | 0.8.0 |
| **前端界面** | Next.js 15 + React 19 + TypeScript | 0.2.0 |
| **数据库** | PostgreSQL + SQLAlchemy | - |
| **AI 引擎** | NVIDIA AI Foundation Models (Llama 3.1 405B) | - |
| **缓存** | 内存缓存 + TTL | - |

---

## ✅ 已实现功能

### Phase 1: 核心 SOC 功能 ✅

#### 1.1 告警分析与处理
- **智能告警分析** (`/api/analyze-alert`)
  - AI 驱动的告警分类与严重性评估
  - 自动提取 IOCs (IP、域名、URL、Hash)
  - 生成证据点和建议操作
  - 影响分析和业务影响评估
  
- **时间线构建** (`/api/build-timeline`)
  - 从原始日志提取事件时间线
  - 识别可疑 TOP5 事件
  - 生成下一步调查建议

#### 1.2 资产管理
- **资产清单管理** (`/api/assets`)
  - 主机、IP、负责人的全生命周期管理
  - 业务关键性分级 (low/medium/high/critical)
  - 标签系统和备注功能
  - 批量导入/导出

#### 1.3 IOC 管理
- **IOC 命中追踪** (`/api/ioc-hits`)
  - 自动关联告警与资产
  - 支持手动添加 IOC
  - 历史记录查询
  - 多维度分析 (按资产、按告警)

#### 1.4 历史记录
- **操作历史** (`/api/history`)
  - 所有分析操作的完整记录
  - 支持按模块筛选和搜索
  - 可导出为 Markdown
  - 一键清理功能

---

### Phase 2: AI Copilot 智能助手 ✅

#### 2.1 AI 驱动的分析服务
- **智能告警分析** - 使用 NVIDIA Llama 3.1 405B 模型
- **自然语言查询** - 用自然语言查询 SOC 数据
- **Playbook 推荐** - 基于告警类型推荐响应流程
- **对话式交互** - 支持多轮对话的安全助手

#### 2.2 支持的 AI Provider
- ✅ **NVIDIA AI** (推荐) - Llama 3.1 405B/70B/8B
- ✅ **Zhipu AI** (智谱AI) - GLM-4
- ✅ **Anthropic Claude** - Claude 3 Opus
- ✅ **OpenAI** - GPT-4

#### 2.3 报告生成
- **自动报告生成**
  - 工单模板 (Jira/ServiceNow)
  - 日报模板
  - 事后分析模板

---

### Phase 3: 高级分析 ✅

#### 3.1 UEBA 用户行为分析 (`/api/ueba`)
- **异常检测** - 基于 ML 的行为异常识别
- **用户风险画像** - 动态风险评估
- **高风险用户列表** - 自动识别内部威胁
- **基线建立** - 自适应行为基线
- **Dashboard** - 可视化风险仪表板

**支持的异常类型**:
- 非工作时间登录
- 异常数据访问
- 地理位置异常
- 权限提升尝试

#### 3.2 威胁狩猎 (`/api/threat-hunting`)
- **假设驱动狩猎** - 支持狩猎假设管理
- **自动狩猎执行** - 基于 IOC 的自动调查
- **IOC 狩猎** - 批量 IOC 查询
- **狩猎结果追踪** - 完整的狩猎历史

---

### Phase 4: 生态系统 ✅

#### 4.1 Playbook Marketplace (`/api/marketplace`)
- **Playbook 商店** - 社区共享的响应流程
- **分类浏览** - 按场景分类 (合规、响应、调查等)
- **下载统计** - 热门 Playbook 排行
- **评分评论** - 社区反馈系统
- **精选推荐** - 官方认证 Playbook

**内置 Playbook 示例**:
1. 恶意软件事件响应
2. 数据泄露调查
3. 钓鱼邮件分析
4. 内部威胁调查
5. 合规审计检查
6. 勒索软件响应

#### 4.2 Cloud Native 安全 (`/api/cloud-native`)
- **容器安全扫描** - Docker/Kubernetes 镜像扫描
- **K8s 资源审计** - 集群安全配置检查
- **云事件监控** - AWS/Azure/GCP 安全事件
- **合规报告** - CIS、NIST 合规性检查
- **云安全 Dashboard**

---

### v0.7: 高级 Playbook 引擎 ✅

#### 5.1 DAG 工作流引擎
- **可视化流程编排** - 节点拖拽式编辑
- **条件分支** - 支持 if/else 逻辑
- **并行执行** - 多节点同时运行
- **失败重试** - 可配置重试策略

#### 5.2 节点类型
| 类型 | 功能 |
|------|------|
| **START** | 流程起点 |
| **END** | 流程终点 |
| **HTTP** | HTTP API 调用 |
| **TRANSFORM** | 数据转换 |
| **CONDITION** | 条件判断 |
| **DELAY** | 延时等待 |
| **PARALLEL** | 并行分支 |
| **NOTIFICATION** | 消息通知 |

#### 5.3 版本管理
- **版本发布** - 支持发布稳定版本
- **版本回滚** - 一键恢复到历史版本
- **变更记录** - 完整的版本历史

#### 5.4 触发器系统
- **Webhook 触发** - 外部系统集成
- **定时任务** (Cron) - 周期自动化
- **秘密管理** - 加密存储 API Keys

---

## 🆕 近期升级内容

### 2026-02-11 更新

#### 🔧 功能修复
1. **AI Provider 配置修复**
   - 修复了 `AI_PROVIDER` → `ai_provider` 属性名问题
   - 现在正确读取环境变量配置

2. **API 路由修复**
   - 添加了缺失的 marketplace、threat_hunting、ueba、cloud_native 路由
   - 修复了 Phase 3/4 模块的导入问题

3. **前端 API 修复**
   - 添加了 `api.post()` 方法
   - 修复了 AI Assistant 页面的响应处理
   - 修复了 `response.data` → `response` 的解构问题

#### 📦 依赖更新
1. **scikit-learn 安装**
   - 版本: 1.4.0
   - 启用 Phase 3 UEBA 和威胁狩猎功能

2. **NVIDIA AI 集成**
   - 添加了 NVIDIAProvider 类
   - 支持 NVIDIA AI Foundation Models API
   - 默认模型: Llama 3.1 405B

#### ⚙️ 配置更新
- **`.env` 配置**
  ```env
  AI_PROVIDER=nvidia
  NVIDIA_API_KEY=nvapi-xxxxxxxx
  NVIDIA_MODEL=meta/llama-3.1-405b-instruct
  ```

---

## 📊 系统状态

### API 端点统计
- **总路由数**: 104 个
- **Phase 1 核心**: 35 个
- **Phase 2 AI**: 8 个
- **Phase 3 分析**: 12 个
- **Phase 4 生态**: 18 个
- **v0.7 Playbook**: 31 个

### AI 服务状态
```json
{
  "status": "available",
  "provider": "nvidia",
  "model": "meta/llama-3.1-405b-instruct",
  "features": [
    "alert_analysis",
    "natural_language_query", 
    "playbook_recommendation",
    "chat",
    "report_generation"
  ]
}
```

---

## 🚀 访问地址

| 服务 | URL | 说明 |
|------|-----|------|
| **前端界面** | http://localhost:3003 | Web UI |
| **后端 API** | http://localhost:8001 | REST API |
| **API 文档** | http://localhost:8001/docs | Swagger UI |
| **健康检查** | http://localhost:8001/api/health | 服务状态 |

### 默认登录
- **用户名**: `admin`
- **密码**: `admin123!`

---

## 📁 项目结构

```
sec/
├── backend/                      # 后端服务
│   ├── routers/                  # API 路由
│   │   ├── ai.py                # AI Copilot
│   │   ├── marketplace.py       # Playbook 商店
│   │   ├── ueba.py              # UEBA 分析
│   │   ├── threat_hunting.py    # 威胁狩猎
│   │   └── cloud_native.py      # 云原生安全
│   ├── services/                # 业务逻辑
│   │   ├── ai_providers.py      # LLM Provider
│   │   ├── ai_service_enhanced.py
│   │   └── ueba_service.py
│   ├── core/                    # 核心配置
│   │   └── config.py
│   └── .env                     # 环境配置
├── frontend/                     # 前端应用
│   ├── app/                     # Next.js App Router
│   │   ├── ai-assistant/        # AI 助手页面
│   │   ├── marketplace/         # Playbook 商店
│   │   └── ...
│   ├── components/              # React 组件
│   └── lib/api.ts              # API 客户端
└── README.md
```

---

## 🔮 下一步计划

### 短期 (v0.8.x)
- [ ] 完善前端 AI Assistant 页面交互
- [ ] 添加 Playbook Marketplace 评分功能
- [ ] 优化 AI 响应速度
- [ ] 添加更多内置 Playbook

### 中期 (v0.9.x)
- [ ] 集成 Vector DB (ChromaDB) 用于 RAG
- [ ] 添加更多 Cloud Provider 支持
- [ ] 实现实时告警推送 (WebSocket)
- [ ] 添加 SSO/OAuth 认证

### 长期 (v1.0)
- [ ] SOAR 自动化编排
- [ ] 威胁情报平台集成
- [ ] 多租户支持
- [ ] 生产环境部署文档

---

## 📞 技术支持

如有问题，请检查:
1. 后端服务是否运行: `curl http://localhost:8001/api/health`
2. AI 配置是否正确: 检查 `.env` 文件
3. 前端缓存: 尝试 Ctrl+F5 强制刷新
4. 查看后端日志: `backend/backend.log`

---

**文档结束**
