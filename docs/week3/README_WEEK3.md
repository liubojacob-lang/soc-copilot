# Week 3 开发计划 - 离线消息缓存与高级功能

**项目**: SOC Copilot
**Week**: 3
**预估周期**: 4-5 天
**依赖**: Week 2 完成（WebSocket 实时告警流）

---

## 📋 Week 3 概述

在 Week 2 成功实现 WebSocket 实时告警流的基础上，Week 3 将专注于**提升系统可靠性**和**增强用户体验**，主要实现离线消息缓存、服务端消息过滤、监控告警等功能。

---

## 🎯 Week 3 目标

### 主要目标
1. **离线消息缓存** - 解决客户端断线期间的告警丢失问题
2. **服务端消息过滤** - 减少不必要的网络传输和客户端处理
3. **监控和告警** - 实时监控 WebSocket 连接状态和消息吞吐
4. **性能优化** - 消息压缩、批量发送等优化措施

### 成功标准
- [ ] 客户端重连后能接收离线期间的告警
- [ ] 支持服务端过滤规则（按严重级别、事件类型等）
- [ ] 实时监控仪表板显示连接状态和消息统计
- [ ] 消息吞吐提升 50%+

---

## 📅 详细计划

### Day 1: 离线消息缓存架构（6-8 小时）

#### 任务列表
- [ ] 设计消息队列架构
- [ ] 实现消息缓存服务
- [ ] 集成到 WebSocket 路由
- [ ] 编写单元测试

#### 技术设计

**架构选择**: Redis 作为消息队列后端

```python
# 消息队列结构
user:{user_id}:queue -> List[WebSocketMessage]
TTL: 24 小时
Max Size: 1000 条消息/用户
```

**数据流**:
```
1. 告警产生 → 检查连接状态
2. 如果离线 → 加入消息队列
3. 客户端重连 → 发送队列中的消息
4. 发送完成 → 清空队列
```

**新增组件**:
- `backend/services/message_queue.py` - 消息队列服务
- `backend/models/message_queue.py` - 消息队列模型

#### API 设计

**缓存消息**:
```python
async def cache_message(user_id: str, message: WebSocketMessage):
    """缓存离线消息"""
    await message_queue.push(user_id, message)
```

**获取缓存消息**:
```python
async def get_cached_messages(user_id: str) -> List[WebSocketMessage]:
    """获取用户的缓存消息"""
    return await message_queue.pop_all(user_id)
```

#### 测试计划
- [ ] 缓存消息成功
- [ ] 重连后自动接收缓存消息
- [ ] TTL 过期自动清理
- [ ] 队列大小限制

---

### Day 2: 服务端消息过滤（6-8 小时）

#### 任务列表
- [ ] 设计过滤规则 schema
- [ ] 实现服务端过滤引擎
- [ ] 集成到 WebSocket 路由
- [ ] 前端过滤配置 UI

#### 过滤规则设计

```python
class FilterRule(BaseModel):
    """消息过滤规则"""
    user_id: str
    min_severity: Optional[SeverityLevel] = None
    max_severity: Optional[SeverityLevel] = None
    event_types: Optional[List[str]] = None
    agent_ids: Optional[List[str]] = None
    source_ips: Optional[List[str]] = None
    enable_aggregation: bool = True
```

#### 实现逻辑

```python
async def should_send_message(
    user_id: str,
    message: WebSocketMessage,
    filters: FilterRule
) -> bool:
    """检查消息是否应该发送给用户"""
    alert = message.data

    # 严重级别过滤
    if filters.min_severity and alert.severity < filters.min_severity:
        return False

    # 事件类型过滤
    if filters.event_types and alert.event_type not in filters.event_types:
        return False

    # 代理过滤
    if filters.agent_ids and alert.agent.id not in filters.agent_ids:
        return False

    return True
```

#### API 设计

**设置过滤规则**:
```http
PUT /api/v1/websocket/filters
Authorization: Bearer <token>
Content-Type: application/json

{
  "min_severity": "high",
  "event_types": ["malware", "ssh_bruteforce"],
  "enable_aggregation": true
}
```

**获取过滤规则**:
```http
GET /api/v1/websocket/filters
Authorization: Bearer <token>
```

#### 前端 UI

过滤配置面板：
- 严重级别选择器
- 事件类型多选框
- 代理 ID 输入
- 启用/禁用聚合开关

---

### Day 3: 监控和告警（6-8 小时）

#### 任务列表
- [ ] 设计监控 metrics
- [ ] 实现监控数据收集
- [ ] 创建监控仪表板
- [ ] 配置告警规则

#### 监控指标

**连接指标**:
- 当前活跃连接数
- 历史连接趋势
- 连接成功率
- 平均连接时长
- 重连次数

**消息指标**:
- 消息发送速率（msg/s）
- 消息接收速率（msg/s）
- 消息延迟（P50, P95, P99）
- 消息队列大小
- 缓存消息数

**错误指标**:
- 连接失败率
- 消息发送失败率
- 异常次数

#### 数据收集

```python
class WebSocketMetrics:
    """WebSocket 监控指标"""

    def __init__(self):
        self.connections = Counter('ws_connections_total')
        self.messages_sent = Counter('ws_messages_sent_total')
        self.message_latency = Histogram('ws_message_latency_seconds')
        self.errors = Counter('ws_errors_total')

    def record_connection(self, user_id: str):
        """记录连接"""
        self.connections.labels(user_id=user_id).inc()

    def record_message_sent(self, msg_type: str):
        """记录消息发送"""
        self.messages_sent.labels(type=msg_type).inc()

    def record_latency(self, latency: float):
        """记录延迟"""
        self.message_latency.observe(latency)
```

#### 监控仪表板

**页面**: `/dashboard/websocket`

**组件**:
1. **连接状态卡片**
   - 当前连接数
   - 连接趋势图（24小时）
   - 在线/离线用户列表

2. **消息统计卡片**
   - 消息发送速率（实时）
   - 消息接收速率（实时）
   - 消息延迟分布
   - 队列大小

3. **错误监控卡片**
   - 错误率趋势
   - 最近错误列表
   - 错误类型分布

4. **实时日志流**
   - WebSocket 连接日志
   - 消息发送日志
   - 错误日志

#### 告警规则

```python
class AlertRule(BaseModel):
    """告警规则"""
    name: str
    condition: str  # "connections > 100" or "error_rate > 5%"
    severity: SeverityLevel
    notification_channels: List[str]  # ["email", "slack"]
    enabled: bool = True
```

**预置告警**:
- 连接数异常（> 100 或 < 5）
- 错误率过高（> 5%）
- 消息队列积压（> 1000）
- 延迟过高（P99 > 1s）

---

### Day 4: 性能优化（6-8 小时）

#### 任务列表
- [ ] 实现消息压缩
- [ ] 批量发送优化
- [ ] 连接复用
- [ ] 性能测试

#### 1. 消息压缩

**实现**: 使用 gzip 压缩消息体

```python
def compress_message(data: dict) -> bytes:
    """压缩消息数据"""
    json_str = json.dumps(data)
    return gzip.compress(json_str.encode())

async def send_compressed(websocket: WebSocket, data: dict):
    """发送压缩消息"""
    compressed = compress_message(data)
    await websocket.send_text(compressed)
```

**预期效果**: 消息大小减少 60-80%

#### 2. 批量发送

**实现**: 累积消息后批量发送

```python
class BatchMessageSender:
    """批量消息发送器"""

    def __init__(self, batch_size: int = 10, max_wait: float = 0.5):
        self.batch_size = batch_size
        self.max_wait = max_wait
        self.buffer: List[dict] = []

    async def add_message(self, message: dict):
        """添加消息到缓冲区"""
        self.buffer.append(message)

        if len(self.buffer) >= self.batch_size:
            await self.flush()

    async def flush(self):
        """发送缓冲区中的所有消息"""
        if self.buffer:
            batch = {
                "type": "batch",
                "messages": self.buffer,
                "count": len(self.buffer)
            }
            # 发送批量消息
            await websocket.send_json(batch)
            self.buffer.clear()
```

**预期效果**: 减少 80% 的 WebSocket 调用

#### 3. 连接复用

**实现**: 共享连接池

```python
class WebSocketConnectionPool:
    """WebSocket 连接池"""

    def __init__(self, max_connections: int = 100):
        self.max_connections = max_connections
        self.connections: Dict[str, WebSocket] = {}

    async def get_connection(self, user_id: str) -> WebSocket:
        """获取用户的连接"""
        if user_id in self.connections:
            return self.connections[user_id]

        # 创建新连接
        ws = await create_websocket(user_id)
        self.connections[user_id] = ws
        return ws
```

#### 性能测试目标

| 指标 | Week 2 | Week 3 目标 | 提升 |
|------|--------|------------|------|
| 消息吞吐 | 16 msg/s | 24 msg/s | +50% |
| 连接数 | 20 | 50 | +150% |
| 延迟 P99 | <100ms | <50ms | -50% |
| 带宽使用 | 1KB/alert | 0.3KB/alert | -70% |

---

### Day 5: 测试和文档（4-6 小时）

#### 任务列表
- [ ] 端到端测试
- [ ] 性能测试
- [ ] 压力测试
- [ ] 用户文档更新
- [ ] Week 3 总结报告

#### 测试计划

**端到端测试**:
- [ ] 离线消息缓存流程
- [ ] 服务端过滤功能
- [ ] 监控仪表板数据
- [ ] 性能优化验证

**性能测试**:
- [ ] 消息压缩效果
- [ ] 批量发送性能
- [ ] 并发连接数
- [ ] 消息吞吐量

**压力测试**:
- [ ] 100 并发连接
- [ ] 100 msg/s 持续发送
- [ ] 内存泄漏检测
- [ ] 长时间运行稳定性

---

## 🔧 技术架构

### 组件关系

```
┌─────────────────────────────────────────────────────────┐
│                    Frontend Clients                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐             │
│  │ Browser 1│  │ Browser 2│  │ Browser N│             │
│  └─────┬────┘  └─────┬────┘  └─────┬────┘             │
└────────┼──────────────┼──────────────┼─────────────────┘
         │              │              │
         │ WebSocket    │ WebSocket    │ WebSocket
         │              │              │
┌────────▼────────────────────────────────────────────────┐
│               WebSocket Router (/ws/alerts)             │
│  ┌─────────────────────────────────────────────────┐   │
│  │        Connection Manager                        │   │
│  │  - Active connections                           │   │
│  │  - Channel subscriptions                        │   │
│  └─────────────────────────────────────────────────┘   │
│         │                                             │
│  ┌──────▼──────────┐  ┌──────────────────────────┐    │
│  │ Message Filter  │  │  Message Queue Service   │    │
│  │  - Server-side  │  │  - Redis backend         │    │
│  │  filtering      │  │  - Offline message       │    │
│  └─────────────────┘  │    caching               │    │
│                      └──────────────────────────┘    │
│         │                                             │
│  ┌──────▼──────────────────────────────────┐         │
│  │       Stream Service                     │         │
│  │  - Alert aggregation                    │         │
│  │  - Broadcasting                         │         │
│  └─────────────────────────────────────────┘         │
└───────────────────────────────────────────────────────┘
         │
┌────────▼──────────────────────────────────────────┐
│         Monitoring Service                        │
│  ┌──────────────┐  ┌──────────────┐             │
│  │  Metrics     │  │  Alerting    │             │
│  │  Collection  │  │  Engine      │             │
│  └──────────────┘  └──────────────┘             │
└───────────────────────────────────────────────────┘
```

### 数据流

**在线消息流**:
```
Alert → Stream Service → Filter Check → Broadcast → Clients
```

**离线消息流**:
```
Alert → Stream Service → Check Online Status
  → (Offline) → Message Queue
  → Client Reconnect → Send Cached Messages
```

**监控数据流**:
```
WebSocket Events → Metrics Collector → Time Series DB
  → Monitoring Dashboard → Visualization
```

---

## 📊 预期成果

### 功能增强

1. **离线消息缓存**
   - ✅ 客户端重连后自动接收离线消息
   - ✅ 最多缓存 1000 条消息/用户
   - ✅ 24 小时 TTL

2. **服务端过滤**
   - ✅ 减少不必要的网络传输
   - ✅ 按严重级别、事件类型过滤
   - ✅ 动态过滤规则配置

3. **监控告警**
   - ✅ 实时连接状态监控
   - ✅ 消息吞吐监控
   - ✅ 异常自动告警

4. **性能优化**
   - ✅ 消息压缩（减少 70% 带宽）
   - ✅ 批量发送（提升 50% 吞吐）
   - ✅ 支持 50+ 并发连接

### 性能目标

| 指标 | Week 2 | Week 3 | 提升 |
|------|--------|--------|------|
| 消息吞吐 | 16 msg/s | 24+ msg/s | +50% |
| 并发连接 | 20 | 50+ | +150% |
| P99 延迟 | <100ms | <50ms | -50% |
| 带宽使用 | 1KB/alert | 0.3KB/alert | -70% |

---

## 🛠️ 技术栈

### 新增依赖

**后端**:
```python
# requirements.txt
redis==5.0.0              # 消息队列
prometheus-client==0.19.0 # 监控指标
gzipio==0.1.0             # 消息压缩
```

**前端**:
```json
{
  "dependencies": {
    "recharts": "^2.10.0"      // 监控图表
    "use-query": "^3.39.0"     // 数据查询
  }
}
```

### 基础设施

**Redis**:
- 用途：消息队列、缓存
- 部署：Docker 容器
- 配置：最大内存 1GB

**Prometheus**（可选）:
- 用途：监控数据存储
- 部署：Docker 容器
- 保留时间：7 天

---

## 📁 文件清单

### 新增文件

**后端**:
- `backend/services/message_queue.py` - 消息队列服务
- `backend/services/websocket_filter.py` - 服务端过滤
- `backend/services/websocket_metrics.py` - 监控指标
- `backend/services/alerting_engine.py` - 告警引擎
- `backend/routers/websocket_filters.py` - 过滤 API
- `backend/routers/monitoring.py` - 监控 API

**前端**:
- `frontend/app/[locale]/dashboard/websocket/page.tsx` - 监控仪表板
- `frontend/components/websocket/FilterConfig.tsx` - 过滤配置组件
- `frontend/components/websocket/MetricsChart.tsx` - 指标图表

### 修改文件

**后端**:
- `backend/routers/websocket.py` - 集成消息队列和过滤
- `backend/requirements.txt` - 添加新依赖

**前端**:
- `frontend/components/wazuh/WazuhAlertStream.tsx` - 支持离线消息

### 文档

- `docs/week3/README_WEEK3.md` - Week 3 计划
- `docs/MESSAGE_QUEUE_GUIDE.md` - 消息队列使用指南
- `docs/FILTER_CONFIG_GUIDE.md` - 过滤配置指南
- `docs/WEB_SOCKET_MONITORING.md` - 监控使用指南

---

## ⚠️ 风险和挑战

### 技术风险

1. **Redis 依赖**
   - **风险**: Redis 故障导致消息丢失
   - **缓解**: Redis 持久化 + 主从复制

2. **性能回归**
   - **风险**: 新功能导致性能下降
   - **缓解**: 充分的性能测试

3. **复杂度增加**
   - **风险**: 代码复杂度提高，维护困难
   - **缓解**: 良好的代码结构和文档

### 时间风险

- **风险**: 功能复杂，可能超期
- **缓解**: 分阶段实施，优先级管理

---

## 🚀 部署建议

### 开发环境

```bash
# 1. 启动 Redis
docker run -d -p 6379:6379 redis:7-alpine

# 2. 配置环境变量
export REDIS_URL=redis://localhost:6379/0
export ENABLE_MESSAGE_QUEUE=true

# 3. 启动后端
cd backend
python3 -m uvicorn main:app --reload
```

### 生产环境

```yaml
# docker-compose.yml
services:
  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
    deploy:
      resources:
        limits:
          memory: 1G

  backend:
    environment:
      - REDIS_URL=redis://redis:6379/0
      - ENABLE_MESSAGE_QUEUE=true
      - MESSAGE_QUEUE_TTL=86400
    depends_on:
      - redis
```

---

## ✅ 验收标准

### 功能验收

- [ ] 离线消息缓存正常工作
- [ ] 服务端过滤功能正常
- [ ] 监控仪表板数据准确
- [ ] 性能优化达到目标

### 性能验收

- [ ] 消息吞吐 ≥ 24 msg/s
- [ ] 并发连接 ≥ 50
- [ ] P99 延迟 < 50ms
- [ ] 带宽使用减少 ≥ 70%

### 质量验收

- [ ] 所有测试通过
- [ ] 代码审查通过
- [ ] 文档完整
- [ ] 生产就绪

---

## 📞 联系方式

**技术负责人**: SOC Copilot Team
**问题反馈**: GitHub Issues
**文档**: `/docs/week3/`

---

**创建日期**: 2026-02-25
**计划开始**: Week 3
**预估完成**: 4-5 天
**状态**: 📝 计划中

