# SOC Copilot - 统一技术文档

> **版本**: v0.9.0 | **更新日期**: 2026-02-25 | **维护团队**: SOC Team

---

## 目录

1. [项目概述](#1-项目概述)
2. [技术架构](#2-技术架构)
3. [核心功能模块](#3-核心功能模块)
4. [API参考](#4-api参考)
5. [部署指南](#5-部署指南)
6. [安全监控集成](#6-安全监控集成)
7. [前后端功能对照](#7-前后端功能对照)
8. [实施进度报告](#8-实施进度报告)
9. [测试报告](#9-测试报告)
10. [优化建议与路线图](#10-优化建议与路线图)

---

## 1. 项目概述

### 1.1 项目简介

SOC Copilot 是一个面向安全运营中心(SOC)团队的智能分析工作台，提供告警分析、事件时间线重建、报告生成、资产管理、威胁情报查询及 Playbook 自动化编排能力。

### 1.2 技术栈

| 层级 | 技术 | 版本 |
|------|------|------|
| **前端框架** | Next.js | 15.1 |
| **UI库** | React | 19.0 |
| **类型系统** | TypeScript | 5.x |
| **样式框架** | Tailwind CSS | 3.4.17 |
| **DAG可视化** | React Flow | 11.11.4 |
| **后端框架** | FastAPI | 0.115.0 |
| **ORM** | SQLAlchemy | 2.0.36 |
| **数据库** | PostgreSQL/SQLite | - |
| **缓存** | Redis | 7+ |
| **AI提供商** | Anthropic, Zhipu, NVIDIA, Moonshot, OpenRouter | - |

### 1.3 快速开始

**环境要求**: Python 3.10+, Node.js 18+

**后端启动**:
```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**前端启动**:
```bash
cd frontend
npm install && npm run dev
```

**访问地址**:

| 服务 | URL | 默认凭证 |
|------|-----|----------|
| 前端 | http://localhost:3003 | admin / admin123 |
| API文档 | http://localhost:8000/docs | - |
| 数据库 | `data/app.db` | 自动创建 |

---

## 2. 技术架构

### 2.1 系统架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                         前端层 (Next.js)                          │
│  TypeScript / Tailwind CSS / i18n / React Flow                  │
└───────────────────────────┬─────────────────────────────────────┘
                            │ HTTP/WebSocket
┌───────────────────────────▼─────────────────────────────────────┐
│                      API网关层 (FastAPI)                          │
│  Pydantic / 中间件 (Auth, Audit, Rate Limit, CSRF)               │
└───────────────────────────┬─────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
┌───────▼────────┐  ┌──────▼──────┐  ┌────────▼────────┐
│   核心APIs     │  │  AI/ML APIs │  │  集成APIs       │
│  Auth/Users    │  │  LLM/RAG    │  │  Wazuh/Dify    │
│  Assets/Alerts │  │  Tasks      │  │  Cloud/OTX     │
└───────┬────────┘  └──────┬──────┘  └────────┬────────┘
        └──────────────────┼───────────────────┘
                           │
┌──────────────────────────▼─────────────────────────────────────┐
│                     服务层 (Business Logic)                      │
│  Playbook引擎 / 威胁情报 / 事件关联 / UEBA / 通知服务            │
└───────────────────────────┬─────────────────────────────────────┘
                            │
        ┌───────────────────┼──────────────────┐
        │                   │                  │
┌───────▼────────┐  ┌──────▼──────┐  ┌───────▼────────┐
│  PostgreSQL    │  │   Redis     │  │  Vector DB     │
│  数据持久化    │  │  缓存/队列  │  │  RAG嵌入       │
└────────────────┘  └─────────────┘  └────────────────┘
```

### 2.2 设计模式

| 模式 | 用途 | 示例 |
|------|------|------|
| **Repository** | 数据访问抽象 | `PlaybookDefinitionRepository` |
| **Service Layer** | 业务逻辑封装 | `AlertLifecycleService` |
| **Factory** | AI提供商实例化 | `LLMFactory.create_provider()` |
| **Strategy** | Playbook节点执行 | 各节点类型的Executor |
| **Observer** | WebSocket实时更新 | `WebSocketManager` |

### 2.3 认证授权

**认证流程**:
```
POST /api/auth/login → 验证凭证 → 生成JWT → 返回Token
                                    ↓
客户端携带Token → 中间件验证 → 注入当前用户到路由
```

**角色权限**:
- `ADMIN` - 完全系统访问
- `AUDITOR` - 只读审计访问
- `ANALYST` - 标准SOC操作
- `USER` - 基本访问

---

## 3. 核心功能模块

### 3.1 告警分析器 (Alert Analyzer)

- 事件分类（支持9种安全事件类型）
- 严重性评估
- **双引擎IOC提取**（本地正则 + AI提取IP、域名、URL、哈希）
- 实体识别（用户、主机、进程）
- 证据提取和修复建议
- 影响分析面板（风险评分、关联资产）

### 3.2 时间线构建器 (Timeline Builder)

- 自动事件时间线重建
- 智能可疑事件排名（Top 5）
- 下一步调查建议

### 3.3 报告生成器 (Report Writer)

- 工单模板
- 日报模板
- 事后分析模板

### 3.4 资产管理 (Asset Management)

- 完整CRUD操作
- 批量导入（JSON格式）
- 多维度搜索（主机名、IP、所有者、业务线、标签）
- 资产关键性分级（Low/Medium/High/Critical）

### 3.5 威胁情报 (Threat Intelligence)

- AlienVault OTX集成
- 本地缓存（7天TTL）
- 合规过滤（私有IP、内部域名阻止）

### 3.6 Playbook自动化引擎

**v0.7.4 新特性**:
- **节点插件系统**: 动态节点类型注册，从 `plugins/` 目录自动加载
- **密钥管理**: Fernet加密存储，支持 `{{secret.xxx}}` 变量引用
- **运行恢复**: 服务重启后自动检测孤儿运行并恢复
- **执行队列**: 系统级并发控制（max_concurrent=3），FIFO策略
- **HTTP沙箱**: 主机名白名单（阻止localhost、私有IP）
- **5个内置插件**: HTTP Request, OTX Lookup, Decision, Slack Notify, Human Approval

**DAG工作流引擎**:
- 可视化DAG编辑器（React Flow）
- 多种节点类型：触发器（Webhook、Cron）、处理（IOC提取、威胁情报查询）、决策、动作、控制
- 执行模式：`dry_run`（模拟）/ `apply`（实际执行）

### 3.7 事件关联引擎

- 时间窗口关联
- MITRE ATT&CK Kill Chain关联
- 威胁情报关联
- 关联组管理

### 3.8 UEBA用户行为分析

- 异常登录时间/地点检测
- 大量数据下载检测
- 未授权资源访问检测
- 横向移动检测
- 权限提升检测

---

## 4. API参考

### 4.1 核心端点

| 方法 | 端点 | 描述 |
|------|------|------|
| POST | `/api/analyze-alert` | 告警分析 |
| POST | `/api/build-timeline` | 构建时间线 |
| POST | `/api/generate-report` | 生成报告 |
| GET | `/api/health` | 健康检查 |

### 4.2 告警管理

| 方法 | 端点 | 描述 |
|------|------|------|
| GET | `/api/v1/alerts` | 告警列表 |
| GET | `/api/v1/alerts/{id}` | 告警详情 |
| PATCH | `/api/v1/alerts/{id}/status` | 更新状态 |
| POST | `/api/v1/alerts/{id}/assign` | 分配告警 |
| POST | `/api/v1/alerts/{id}/resolve` | 解决告警 |
| POST | `/api/v1/alerts/batch/update` | 批量更新 |

### 4.3 Playbook管理

| 方法 | 端点 | 描述 |
|------|------|------|
| GET | `/api/playbook-definitions` | 定义列表 |
| POST | `/api/playbook-definitions` | 创建定义 |
| POST | `/api/playbook-definitions/{id}/run` | 执行定义 |
| GET | `/api/playbook/runs` | 执行历史 |
| POST | `/api/playbook/runs/{run_id}/cancel` | 取消执行 |

### 4.4 触发器管理

| 方法 | 端点 | 描述 |
|------|------|------|
| GET | `/api/triggers` | 触发器列表 |
| POST | `/api/triggers/cron` | 创建Cron触发器 |
| POST | `/api/triggers/webhook` | 创建Webhook触发器 |

### 4.5 密钥管理 (v0.7.4)

| 方法 | 端点 | 描述 |
|------|------|------|
| GET | `/api/secrets` | 密钥列表（仅管理员） |
| POST | `/api/secrets` | 创建密钥 |
| GET | `/api/secrets/key-status` | 加密密钥状态 |

### 4.6 WebSocket实时推送

**端点**: `/api/v1/ws/alerts`

**消息类型**:
- `alert` - 新告警
- `alert_update` - 告警更新
- `playbook_run` - Playbook执行状态
- `system` - 系统通知

---

## 5. 部署指南

### 5.1 本地开发部署

```bash
# 克隆代码
git clone <repository-url> && cd soc-copilot

# 启动服务
docker-compose up -d

# 访问应用
# 前端: http://localhost:3000
# 后端: http://localhost:8000
```

### 5.2 生产部署

```bash
# 配置环境变量
cp .env.example .env.prod

# 部署
./deploy.sh production
```

### 5.3 必需环境变量

```ini
# 数据库
DB_USER=soc_copilot
DB_PASSWORD=your-secure-password
DB_NAME=soc_copilot

# 安全配置
SECRET_KEY=your-secret-key
JWT_SECRET=your-jwt-secret
BOOTSTRAP_ADMIN_PASSWORD=your-admin-password

# AI配置
AI_PROVIDER=zhipu
ZHIPU_API_KEY=your_api_key

# 威胁情报
OTX_API_KEY=your_otx_api_key

# v0.7.4 密钥管理
SECRET_ENCRYPTION_KEY=your_fernet_key
RUN_QUEUE_MAX=3
```

### 5.4 CI/CD配置

**GitHub Secrets**:
- `DOCKERHUB_USERNAME`
- `DOCKERHUB_TOKEN`

**分支策略**:
- `main` - 生产分支，自动部署
- `develop` - 开发分支，部署到测试环境
- `feature/*` - 功能分支，仅运行测试

### 5.5 监控与日志

```bash
# 查看所有服务日志
docker-compose logs -f

# 健康检查
curl http://localhost:8000/api/health

# 数据库备份
docker-compose exec postgres pg_dump -U soc_copilot soc_copilot > backup.sql
```

---

## 6. 安全监控集成

### 6.1 Wazuh SIEM集成

**架构**:
```
Wazuh Agent → Wazuh Manager → Elasticsearch → Log Forwarder → SOC Copilot
```

**Docker Compose配置** (`docker-compose.security.yml`):
```yaml
services:
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.12.0
    ports: ["9200:9200"]
    
  wazuh-manager:
    image: wazuh/wazuh-manager:4.12.0
    ports: ["1514:1514", "55000:55000"]
    
  kibana:
    image: docker.elastic.co/kibana/kibana:8.12.0
    ports: ["5601:5601"]
```

**访问地址**:

| 服务 | 地址 | 凭证 |
|------|------|------|
| Kibana | http://localhost:5601 | 无需认证 |
| Wazuh Dashboard | https://localhost:444 | admin / WazuhP@ssw0rd123! |
| Wazuh API | https://localhost:55000 | wazuh-wui / WazuhP@ssw0rd123! |

### 6.2 告警接收API

```bash
# 发送测试告警
curl -X POST http://localhost:8000/api/v1/security-alerts/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "source": "wazuh",
    "event_id": "test-001",
    "timestamp": "2026-02-24T10:00:00Z",
    "event_type": "web_attack",
    "severity": "high",
    "title": "SQL Injection Attempt",
    "source_ip": "192.168.1.100"
  }'
```

### 6.3 飞书通知配置

**快速配置**:
```bash
# 交互式配置向导
python configure_feishu.py

# 或手动配置
export FEISHU_WEBHOOK_URL=https://open.feishu.cn/open-apis/bot/v2/hook/xxx
```

**验证配置**:
```bash
python test_feishu_quick.py $FEISHU_WEBHOOK_URL
```

---

## 7. 前后端功能对照

### 7.1 统计概览

| 类别 | 数量 |
|------|------|
| 后端路由文件 | 37个 |
| API端点 | 200+ |
| 前端页面 | 28个 |
| 后端服务文件 | 55+ |
| 数据模型 | 28个 |

### 7.2 完全缺失前端页面的功能 (P0/P1)

| 功能 | 后端路由 | 建议页面 | 优先级 |
|------|----------|----------|--------|
| AI任务队列监控 | `/api/v1/ai-tasks` | `/admin/ai-tasks` | 🔴 P0 |
| 系统仪表盘 | `/api/v1/dashboard` | `/admin/dashboard` | 🔴 P0 |
| 关联规则管理 | `/api/v1/correlation/rules` | `/correlation/rules` | 🟡 P1 |
| IOC命中历史 | `/api/v1/ioc-hits` | `/threat-intel/ioc-hits` | 🟡 P1 |
| 历史记录管理 | `/api/v1/history` | `/admin/history` | 🟢 P2 |
| Webhook管理 | `/api/v1/webhooks` | `/settings/webhooks` | 🟢 P2 |
| 导出中心 | `/api/v1/export` | `/admin/export` | 🟡 P1 |

### 7.3 部分实现的前端页面

| 功能 | 当前页面 | 缺失功能 |
|------|----------|----------|
| AI模型管理 | `/ai-assistant` | 模型列表、默认模型设置、连接测试 |
| 告警生命周期 | `/alerts/[id]` | 完整工作流UI、批量操作 |
| 云原生安全 | `/cloud-native` | 容器扫描、K8s资源、合规报告 |
| 威胁狩猎 | `/threat-hunting` | 假设管理、结果保存 |
| 监控页面 | `/monitor` | 实时流、历史管理 |
| 通知系统 | `/settings/notifications` | 渠道状态、队列统计 |

### 7.4 已完整实现的功能

- ✅ 认证和用户管理
- ✅ 资产管理
- ✅ API Keys管理
- ✅ Playbook管理
- ✅ 触发器管理
- ✅ 密钥管理
- ✅ Marketplace
- ✅ UEBA
- ✅ 事件关联

---

## 8. 实施进度报告

### 8.1 P0功能完成情况

| 功能 | 状态 | 完成度 |
|------|------|--------|
| 系统仪表盘 | ✅ 完成 | 100% |
| AI模型管理 | ✅ 完成 | 100% |
| 告警生命周期 | ✅ 完成 | 100% |

### 8.2 P1功能完成情况

**Phase 1: WebSocket实时推送** ✅
- WebSocket连接管理器
- 离线消息缓存
- 告警生命周期服务
- 前端WebSocket组件

**Phase 2: 告警详情页面增强** ✅
- ThreatIntelCard - 威胁情报卡片
- MITREMapping - ATT&CK映射可视化
- CorrelatedAlerts - 关联告警视图
- AlertActions - 响应动作按钮
- TimelineView - 时间线视图
- AlertNotes - 备注系统

**Phase 3: 威胁情报仪表盘** ✅
- TrendsChart - 趋势图表
- SeverityDistribution - 严重程度分布
- TopSources - Top攻击源
- MITREHeatmap - ATT&CK热图
- IOCStats - IOC统计

### 8.3 代码统计

| 指标 | 数值 |
|------|------|
| P1新增代码 | ~6,500行 |
| 新增组件 | 25+个 |
| 新增页面 | 2个 |
| 新增文件 | 15个 |

---

## 9. 测试报告

### 9.1 测试结果总览

| 组件 | 状态 | 备注 |
|------|------|------|
| Elasticsearch | ✅ 通过 | 集群健康green |
| Kibana | ✅ 通过 | 状态available |
| 数据库(SQLite) | ✅ 通过 | CRUD操作正常 |
| 告警模型 | ✅ 通过 | SecurityAlert模型正常 |
| 威胁情报丰富化 | ✅ 通过 | 100%丰富化率 |
| WebSocket路由 | ✅ 通过 | 端点已注册 |
| 生命周期路由 | ✅ 通过 | 路由已注册 |

### 9.2 通知系统测试

| 模块 | 状态 |
|------|------|
| 消息队列管理器 | ✅ 验证通过 |
| 通知服务 | ✅ 验证通过 |
| Alert Worker | ✅ 验证通过 |
| 监控工具 | ✅ 验证通过 |

### 9.3 性能指标

| 指标 | 预期值 | 实际值 |
|------|--------|--------|
| API平均响应时间 | <200ms | 待监控 |
| 前端首屏加载 | <2s | 待测试 |
| 测试覆盖率 | >85% | ~80% |
| 消息处理速度 | ~10,000/h | 待测试 |

---

## 10. 优化建议与路线图

### 10.1 高优先级优化 (P0)

| 项目 | 描述 | 预计耗时 |
|------|------|----------|
| 生产环境安全加固 | 强制检查必需安全配置 | 15分钟 |
| 数据库迁移管理 | 统一数据库文件路径 | 10分钟 |
| Redis高可用配置 | 连接池、健康检查、故障降级 | 30分钟 |

### 10.2 中优先级优化 (P1)

| 项目 | 描述 | 预计耗时 |
|------|------|----------|
| API响应时间监控 | PerformanceMiddleware | 20分钟 |
| 前端错误边界优化 | 添加错误上报 | 15分钟 |
| 审计日志归档 | 自动归档旧日志 | 30分钟 |

### 10.3 实施路线图

**Week 1 (快速见效)**:
- Day 1-2: 关联分析引擎
- Day 3-4: 自动响应编排
- Day 5: Wazuh完整部署

**Week 2 (用户体验)**:
- Day 6-10: 前端界面完善

**Week 3+ (高级功能)**:
- UEBA检测增强
- 报告和合规

### 10.4 版本规划

| 版本 | 里程碑 | 状态 |
|------|--------|------|
| v0.7.x | DAG剧本引擎 | ✅ 完成 |
| v0.8.x | 事件关联引擎 + UEBA | ✅ 完成 |
| v0.9.x | P1功能实施 | ✅ 完成 |
| v1.0.0 | Wazuh深度集成 | 🔄 进行中 |
| v1.1.x | 告警关联分析 | 📅 规划中 |
| v1.2.x | AI告警摘要 | 📅 规划中 |

---

## 附录

### A. 项目结构

```
soc-copilot/
├── backend/                    # 后端服务
│   ├── core/                   # 核心配置
│   ├── db/                     # 数据库
│   ├── models/                 # 数据模型
│   ├── routers/                # API路由
│   ├── services/               # 业务逻辑
│   ├── playbook_engine/        # Playbook引擎
│   └── main.py                 # 应用入口
├── frontend/                   # 前端应用
│   ├── app/                    # Next.js App Router
│   └── components/             # 组件
├── data/                       # 数据目录
├── docs/                       # 文档
└── README.md                   # 项目说明
```

### B. 常用命令

```bash
# 启动后端
cd backend && uvicorn main:app --reload

# 启动前端
cd frontend && npm run dev

# 运行测试
cd backend && pytest --cov=. --cov-report=html

# 启动安全栈
docker-compose -f docker-compose.security.yml up -d

# 查看API文档
open http://localhost:8000/docs
```

### C. 故障排查

| 问题 | 解决方案 |
|------|----------|
| 端口被占用 | `lsof -i :8000` 查找并终止进程 |
| 数据库连接失败 | 检查Docker服务状态 |
| Kibana版本不兼容 | 使用与ES相同的8.12.0版本 |
| API路由未加载 | 重启后端服务 |
| Wazuh启动缓慢 | 等待5-10分钟初始化 |

---

**文档版本**: v1.0 | **生成时间**: 2026-02-25

*本文档由多个项目文档整合而成，消除了冗余内容，优化了逻辑结构。*