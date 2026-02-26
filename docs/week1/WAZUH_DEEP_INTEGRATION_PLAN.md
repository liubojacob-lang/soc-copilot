# Wazuh SIEM 深度集成实施计划

**版本**: v1.0.0
**创建日期**: 2026-02-25
**预计工期**: 6 周
**当前状态**: 规划阶段

---

## 📋 目录

1. [项目概述](#项目概述)
2. [当前集成状态分析](#当前集成状态分析)
3. [集成目标](#集成目标)
4. [技术架构](#技术架构)
5. [功能模块规划](#功能模块规划)
6. [开发任务分解](#开发任务分解)
7. [实施时间表](#实施时间表)
8. [测试计划](#测试计划)
9. [风险评估](#风险评估)
10. [验收标准](#验收标准)

---

## 项目概述

### 目标

将 Wazuh SIEM 深度集成到 SOC Copilot 平台，打造完整的 SIEM + SOAR 一体化安全运营平台。

### 核心价值

- **实时监控**: 从 Wazuh 接收实时安全日志和告警
- **智能分析**: 利用 AI 引擎分析 Wazuh 告警
- **自动化响应**: 通过 Playbook 自动处理 Wazuh 告警
- **关联分析**: 跨多个告警识别攻击链
- **可视化展示**: Timeline 和仪表板展示威胁态势

---

## 当前集成状态分析

### ✅ 已完成的基础集成

| 组件 | 状态 | 功能 |
|------|------|------|
| **Wazuh API Client** | ✅ 完成 | JWT 认证、Agents 管理、告警查询 |
| **Wazuh Alert Mapper** | ✅ 完成 | 告警格式转换、严重性映射 |
| **Log Receiver Service** | ✅ 完成 | 定时轮询、告警采集 |
| **Message Queue** | ✅ 完成 | Redis Streams 优先级队列 |
| **Notification Service** | ✅ 完成 | 飞书/Slack/Email 通知 |
| **前端 Wazuh 页面** | ✅ 完成 | Agent 列表、健康检查 |

### 🔴 待开发的深度集成功能

| 功能模块 | 优先级 | 工作量 | 依赖 |
|----------|--------|--------|------|
| **实时告警流** | P0 | 5 人日 | WebSocket |
| **告警关联分析** | P1 | 8 人日 | 事件关联引擎 |
| **Timeline 可视化** | P1 | 5 人日 | 前端图表库 |
| **MITRE ATT&CK 映射** | P1 | 3 人日 | ATT&CK 数据集 |
| **告警规则管理** | P2 | 4 人日 | Wazuh API |
| **Agent 管理界面** | P2 | 3 人日 | 前端 CRUD |
| **自动化响应 Playbook** | P2 | 6 人日 | Playbook 触发器 |

---

## 集成目标

### 功能目标

1. **实时告警接收**
   - Wazuh 告警 → SOC Copilot 延迟 <30 秒
   - 支持告警批量处理
   - 告警去重和聚合

2. **智能告警分析**
   - AI 自动分析 Wazuh 告警
   - 提取 IOCs 和实体
   - 生成调查建议

3. **告警关联分析**
   - 关联同一来源的告警
   - 识别攻击链模式
   - 跨时间窗口关联

4. **可视化展示**
   - 攻击 Timeline 时间线
   - MITRE ATT&CK 战术视图
   - Agent 健康状态仪表板

5. **自动化响应**
   - 高危告警自动触发 Playbook
   - 自动隔离受感染主机
   - 自动通知相关人员

### 性能目标

| 指标 | 目标值 | 当前值 |
|------|--------|--------|
| 告警接收延迟 | <30 秒 | ~30 秒 (轮询) |
| 告警分析速度 | <5 秒/告警 | ~3 秒 |
| 通知发送速度 | <10 秒 | ~8 秒 |
| 最大支持 Agents | 500+ | 100 (测试) |

---

## 技术架构

### 系统架构图

```
┌──────────────────────────────────────────────────────────────────────────┐
│                           Wazuh SIEM                                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  │
│  │ Agent 1  │  │ Agent 2  │  │ Agent 3  │  │ Agent N  │  │          │  │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘  │          │  │
│       └──────────────┴──────────────┴──────────────┴──────────┘          │
│                                     │                                    │
│                           ┌─────────▼─────────┐                          │
│                           │   Wazuh Manager   │                          │
│                           │   (Events/Alerts) │                          │
│                           └─────────┬─────────┘                          │
│                                     │ HTTPS API                          │
└─────────────────────────────────────┼────────────────────────────────────┘
                                      │
                    ┌─────────────────▼──────────────────┐
                    │    SOC Copilot - Wazuh Gateway    │
                    │  ┌─────────────────────────────┐  │
                    │  │  Real-time Event Receiver   │  │
                    │  │  (Webhook + Polling)        │  │
                    │  └──────────────┬──────────────┘  │
                    └─────────────────┼──────────────────┘
                                      │
                    ┌─────────────────▼──────────────────┐
                    │      Alert Processing Pipeline     │
                    │  ┌─────────────────────────────┐  │
                    │  │  1. Alert Mapper            │  │
                    │  │  2. Deduplicator            │  │
                    │  │  3. Enrichment Service      │  │
                    │  │  4. Correlation Engine      │  │
                    │  └──────────────┬──────────────┘  │
                    └─────────────────┼──────────────────┘
                                      │
                    ┌─────────────────▼──────────────────┐
                    │         Message Queue (Redis)       │
                    │  Critical │ High │ Medium │ Low     │
                    └─────────────────┼──────────────────┘
                                      │
        ┌─────────────────────────────┼─────────────────────────────┐
        │                             │                             │
┌───────▼────────┐         ┌─────────▼──────────┐       ┌─────────▼──────────┐
│  Alert Worker  │         │   AI Analysis      │       │  Playbook Engine   │
│  • Notify      │         │   • Classify       │       │  • Auto-response  │
│  • Store       │         │   • Extract IOCs   │       │  • Remediation    │
└────────────────┘         └────────────────────┘       └────────────────────┘
        │                             │                             │
        └─────────────────────────────┼─────────────────────────────┘
                                      │
                    ┌─────────────────▼──────────────────┐
                    │           PostgreSQL DB             │
                    │  • Alerts    • Events  • Cases      │
                    │  • IOCs      • Assets  • Timeline   │
                    └─────────────────┬──────────────────┘
                                      │
                    ┌─────────────────▼──────────────────┐
                    │         WebSocket Server           │
                    │  (Real-time updates to frontend)   │
                    └────────────────────────────────────┘
```

### 数据流设计

```
Wazuh Alert → Receiver → Mapper → Queue → Worker → DB + Notify
     │           │          │        │        │         │
     │           │          │        │        │         └─► Feishu/Slack/Email
     │           │          │        │        └─► AI Analysis
     │           │          │        └─► Playbook Trigger
     │           │          └─► Alert Enrichment
     │           └─► Deduplication
     └─► WebSocket Push
```

---

## 功能模块规划

### 模块 1: 实时告警流 (Real-time Alert Stream)

**功能描述**:
- 通过 WebSocket 实时推送 Wazuh 告警到前端
- 支持告警过滤、搜索和排序
- 实时显示告警统计和趋势

**技术方案**:
- 后端: WebSocket 服务器 (FastAPI WebSocket)
- 前端: WebSocket 客户端 + 实时更新组件
- 数据格式: JSON 格式的告警对象

**API 设计**:
```typescript
// WebSocket 连接
WS /api/v1/wazuh/alerts/stream

// 消息格式
{
  "type": "alert",
  "data": {
    "id": "alert-123",
    "timestamp": "2026-02-25T10:00:00Z",
    "severity": "high",
    "rule": { "id": 5710, "level": 12 },
    "agent": { "id": "001", "name": "server-01" },
    "mitre": { "tactic": "Credential Access", "technique": "T1110" }
  }
}
```

### 模块 2: 告警关联分析 (Alert Correlation)

**功能描述**:
- 基于规则关联相关告警
- 识别攻击链模式
- 聚合相似告警

**关联规则**:
1. **时间窗口关联**: 同一 IP 在 5 分钟内的多次告警
2. **Agent 关联**: 同一 Agent 的连续告警
3. **规则组关联**: 同一规则组的告警
4. **MITRE 关联**: 同一 ATT&CK 技术的告警

**数据模型**:
```python
class AlertGroup:
    id: str
    alerts: List[str]  # Alert IDs
    correlation_type: str  # time_window, agent, rule_group, mitre
    confidence: float
    first_seen: datetime
    last_seen: datetime
    iocs: List[str]
    tactics: List[str]
```

### 模块 3: Timeline 可视化

**功能描述**:
- 攻击时间线可视化展示
- 支持缩放和时间范围过滤
- 显示攻击阶段和 MITRE 战术

**技术方案**:
- 前端: D3.js 或 Vis.js Timeline
- 后端: Timeline 数据聚合 API

**API 设计**:
```
GET /api/v1/wazuh/timeline?start_time=...&end_time=...&agent_id=...

Response:
{
  "events": [
    {
      "id": "evt-001",
      "timestamp": "2026-02-25T10:00:00Z",
      "type": "alert",
      "severity": "high",
      "title": "SSH Brute Force",
      "description": "...",
      "mitre": { "tactic": "Credential Access", "technique": "T1110" }
    }
  ],
  "groups": [
    {
      "id": "grp-001",
      "type": "attack_chain",
      "start": "2026-02-25T10:00:00Z",
      "end": "2026-02-25T10:15:00Z",
      "stage": "initial_access"
    }
  ]
}
```

### 模块 4: MITRE ATT&CK 映射

**功能描述**:
- Wazuh 告警自动映射到 MITRE ATT&CK
- 显示战术和技术分布
- 攻击链可视化

**数据源**:
- MITRE ATT&CK v14.1
- Wazuh 内置 MITRE 字段
- 自定义映射规则

**展示方式**:
- 战术热力图
- 技术矩阵
- 攻击链时间线

### 模块 5: 告警规则管理

**功能描述**:
- 查看 Wazuh 检测规则
- 自定义规则启用/禁用
- 规则测试和验证

**API 设计**:
```
GET /api/v1/wazuh/rules
GET /api/v1/wazuh/rules/{rule_id}
PATCH /api/v1/wazuh/rules/{rule_id}
POST /api/v1/wazuh/rules/test
```

### 模块 6: Agent 管理界面

**功能描述**:
- Agent 列表和详情
- Agent 状态监控
- Agent 远程命令

**功能点**:
- Agent CRUD 操作
- 实时状态更新
- Agent 分组管理
- 批量操作

### 模块 7: 自动化响应 Playbook

**功能描述**:
- Wazuh 告警自动触发 Playbook
- 预定义响应流程
- 人工审批节点

**触发器配置**:
```yaml
triggers:
  - name: "SSH Brute Force Response"
    source: "wazuh"
    condition:
      rule_id: 5710
      level: ">= 10"
    action:
      playbook_id: "ssh-bruteforce-response"
      auto_run: true
      approval: false
```

---

## 开发任务分解

### Week 1-2: 实时告警流

**任务列表**:
- [ ] 后端 WebSocket 服务器实现 (2 天)
  - WebSocket 路由配置
  - 告警广播机制
  - 连接管理
- [ ] 前端 WebSocket 客户端实现 (1 天)
  - 连接管理
  - 消息处理
  - 重连机制
- [ ] 实时告警流 UI 开发 (2 天)
  - 告警列表组件
  - 过滤和搜索
  - 实时统计卡片
- [ ] 测试和调试 (1 天)

### Week 3: 告警关联分析

**任务列表**:
- [ ] 关联引擎设计 (1 天)
  - 关联规则定义
  - 算法设计
- [ ] 关联引擎实现 (2 天)
  - 时间窗口关联
  - Agent 关联
  - MITRE 关联
- [ ] 关联结果展示 (2 天)
  - 关联告警分组 UI
  - 攻击链可视化
- [ ] 测试和优化 (1 天)

### Week 4: Timeline 可视化

**任务列表**:
- [ ] Timeline 数据 API (1 天)
  - 时间范围查询
  - 数据聚合
- [ ] 前端 Timeline 组件 (2 天)
  - D3.js/Vis.js 集成
  - 时间轴渲染
  - 事件详情展示
- [ ] MITRE 战术视图 (1 天)
  - 战术矩阵
  - 技术分布图
- [ ] 测试和优化 (1 天)

### Week 5: 告警规则和 Agent 管理

**任务列表**:
- [ ] Wazuh 规则管理 API (2 天)
  - 规则查询
  - 规则启用/禁用
  - 规则测试
- [ ] Agent 管理功能 (2 天)
  - Agent 详情
  - 远程命令
  - 批量操作
- [ ] 前端管理界面 (1 天)
- [ ] 测试和调试 (1 天)

### Week 6: 自动化响应和集成测试

**任务列表**:
- [ ] Playbook 触发器配置 (2 天)
  - Wazuh 触发器类型
  - 条件配置
  - 自动执行
- [ ] 端到端集成测试 (2 天)
  - 完整流程测试
  - 性能测试
  - 压力测试
- [ ] 文档编写 (1 天)
- [ ] 部署和上线 (1 天)

---

## 实施时间表

### 甘特图

```
任务                    Week 1   Week 2   Week 3   Week 4   Week 5   Week 6
实时告警流后端          ████
实时告警流前端                  ████
实时告警流测试                      █
告警关联分析引擎                            ████
关联分析UI                                    ███
关联分析测试                                        █
Timeline API                                             ████
Timeline UI                                                    ███
Timeline测试                                                        █
规则和Agent管理API                                                         ████
管理界面                                                                    ██
自动化响应Playbook                                                                  ████
集成测试                                                                              ███
文档和部署                                                                                ██
```

### 里程碑

| 里程碑 | 日期 | 交付物 |
|--------|------|--------|
| M1: 实时告警流完成 | Week 2 结束 | WebSocket 实时推送功能 |
| M2: 关联分析完成 | Week 3 结束 | 告警关联和攻击链识别 |
| M3: Timeline 完成 | Week 4 结束 | 时间线可视化 |
| M4: 管理功能完成 | Week 5 结束 | 规则和 Agent 管理 |
| M5: 集成测试完成 | Week 6 结束 | 完整功能测试报告 |

---

## 测试计划

### 单元测试

- [ ] WebSocket 服务器测试
- [ ] 关联引擎测试
- [ ] Timeline 数据聚合测试
- [ ] 告警映射器测试

### 集成测试

- [ ] Wazuh → SOC Copilot 数据流
- [ ] WebSocket 实时推送
- [ ] 关联分析端到端
- [ ] Playbook 自动触发

### 性能测试

- [ ] 1000 告警/秒处理能力
- [ ] 100 并发 WebSocket 连接
- [ ] 关联分析响应时间 <5 秒
- [ ] Timeline 查询 <2 秒

### 用户验收测试

- [ ] 实时告警监控
- [ ] 攻击链识别
- [ ] Timeline 调查
- [ ] 自动化响应

---

## 风险评估

### 技术风险

| 风险 | 影响 | 概率 | 缓解措施 |
|------|------|------|----------|
| Wazuh API 限流 | 高 | 中 | 增加缓存、调整轮询间隔 |
| WebSocket 连接不稳定 | 中 | 中 | 实现重连机制、降级到轮询 |
| 关联分析性能 | 高 | 低 | 优化算法、增加索引 |
| 前端性能 | 中 | 中 | 虚拟滚动、分页加载 |

### 进度风险

| 风险 | 影响 | 概率 | 缓解措施 |
|------|------|------|----------|
| Wazuh 测试环境不可用 | 高 | 低 | 使用 Mock 数据 |
| 需求变更 | 中 | 中 | 敏捷迭代、分阶段交付 |
| 资源不足 | 高 | 中 | 调整优先级、削减非关键功能 |

---

## 验收标准

### 功能验收

- [ ] Wazuh 告警实时推送延迟 <30 秒
- [ ] 关联分析准确率 >85%
- [ ] Timeline 支持至少 1000 个事件
- [ ] MITRE 映射覆盖 Wazuh 主要规则
- [ ] 自动化响应 Playbook 成功率 >95%

### 性能验收

- [ ] 系统可支持 500+ Wazuh Agents
- [ ] 可处理 1000+ 告警/小时
- [ ] WebSocket 支持 100+ 并发连接
- [ ] API 响应时间 P95 <2 秒

### 文档验收

- [ ] API 文档完整
- [ ] 用户手册更新
- [ ] 运维文档更新
- [ ] 测试报告完整

---

## 附录

### A. 环境配置

```bash
# .env 添加
WAZUH_ENABLED=true
WAZUH_API_URL=https://localhost:55000
WAZUH_API_USERNAME=wazuh-wui
WAZUH_API_PASSWORD=WazuhP@ssw0rd123!

# WebSocket 配置
WS_ENABLED=true
WS_PORT=8002
WS_MAX_CONNECTIONS=100

# 关联分析配置
CORRELATION_ENABLED=true
CORRELATION_TIME_WINDOW=300  # 5 minutes
CORRELATION_MIN_ALERTS=3

# Timeline 配置
TIMELINE_MAX_EVENTS=1000
TIMELINE_DEFAULT_RANGE=24h
```

### B. 数据库迁移

```sql
-- 告警关联表
CREATE TABLE alert_groups (
    id UUID PRIMARY KEY,
    correlation_type VARCHAR(50),
    alert_ids TEXT[],
    confidence FLOAT,
    first_seen TIMESTAMP,
    last_seen TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Timeline 事件缓存表
CREATE TABLE timeline_events (
    id UUID PRIMARY KEY,
    event_data JSONB,
    timestamp TIMESTAMP,
    agent_id VARCHAR(50),
    INDEX idx_timestamp (timestamp)
);
```

### C. 相关文档

- [Wazuh 集成指南](./docs/wazuh_integration.md)
- [API 参考手册](./API_ENDPOINT_REFERENCE.md)
- [前端开发指南](./frontend/)
- [运维手册](./docs/09-ops-deploy.md)

---

**文档版本**: v1.0.0
**最后更新**: 2026-02-25
**负责人**: SOC Copilot Team
