# WebSocket 功能指南

**版本**: v0.9.2
**更新日期**: 2026-02-26

---

## 目录

1. [概述](#概述)
2. [快速开始](#快速开始)
3. [核心功能](#核心功能)
4. [API 参考](#api-参考)
5. [配置指南](#配置指南)
6. [最佳实践](#最佳实践)
7. [故障排除](#故障排除)

---

## 概述

SOC Copilot WebSocket API 提供实时安全告警、playbook 执行更新和系统通知的推送功能。

### 主要特性

✅ **实时告警推送** - 即时接收安全事件告警
✅ **离线消息缓存** - 自动缓存离线期间的消息，重连后自动投递
✅ **服务端消息过滤** - 基于规则过滤接收的消息类型
✅ **监控和告警** - 实时系统健康监控和阈值告警
✅ **性能优化** - 消息压缩、批量发送、连接池

### 支持的通道

| 通道 | 描述 | 消息类型 |
|------|------|----------|
| `alerts` | 安全告警 | alert |
| `playbook_runs` | Playbook执行状态 | playbook_run |
| `system` | 系统通知 | system |

---

## 快速开始

### 1. 连接 WebSocket

```javascript
// WebSocket 连接 URL
const wsUrl = 'ws://localhost:8000/api/v1/ws/alerts?token=YOUR_JWT_TOKEN&channels=alerts,playbook_runs,system';

// 建立连接
const ws = new WebSocket(wsUrl);

// 监听连接打开
ws.onopen = () => {
  console.log('WebSocket connected');
};

// 监听消息
ws.onmessage = (event) => {
  const message = JSON.parse(event.data);
  console.log('Received:', message);

  if (message._compressed) {
    // 处理压缩消息
    const decompressed = decompressMessage(message._data);
    handleMessage(decompressed);
  } else {
    handleMessage(message);
  }
};

// 监听错误
ws.onerror = (error) => {
  console.error('WebSocket error:', error);
};

// 监听关闭
ws.onclose = () => {
  console.log('WebSocket disconnected');
};
```

### 2. 处理消息

```javascript
function handleMessage(message) {
  switch (message.type) {
    case 'alert':
      handleAlert(message.data);
      break;
    case 'playbook_run':
      handlePlaybookRun(message.data);
      break;
    case 'system':
      handleSystemNotification(message.data);
      break;
    default:
      console.log('Unknown message type:', message.type);
  }
}

function handleAlert(alertData) {
  console.log(`Alert: ${alertData.title} (${alertData.severity})`);
  // 显示告警通知
  showNotification(alertData);
}
```

### 3. 订阅/取消订阅通道

```javascript
// 订阅新通道
function subscribeToChannel(channel) {
  ws.send(JSON.stringify({
    type: 'subscribe',
    channels: ['alerts', channel]
  }));
}

// 取消订阅
function unsubscribeFromChannel(channel) {
  const currentChannels = ['alerts', 'playbook_runs', 'system'];
  const newChannels = currentChannels.filter(ch => ch !== channel);

  ws.send(JSON.stringify({
    type: 'subscribe',
    channels: newChannels
  }));
}
```

---

## 核心功能

### 1. 离线消息缓存

当客户端断开连接时，消息会自动缓存到 Redis。重连后，缓存的消息会自动投递。

**缓存配置**:
- TTL: 24 小时
- 最大队列长度: 1000 条消息
- 自动清理过期消息

**使用示例**:
```javascript
// 重连后，会自动收到离线期间的消息
ws.onmessage = (event) => {
  const message = JSON.parse(event.data);

  // 检测是否是离线消息投递通知
  if (message.type === 'system' &&
      message.data.message.includes('Delivered')) {
    console.log('Offline messages delivered');
  }
};
```

### 2. 服务端消息过滤

在服务器端过滤消息，只接收符合条件的通知。

**支持的过滤条件**:
- 严重级别 (min_severity, max_severity)
- 事件类型 (event_types)
- 代理 ID (agent_ids)
- 源 IP (source_ips)
- 内容搜索 (content_search)
- 速率限制 (max_messages_per_minute)

**创建过滤器**:
```http
PUT /api/v1/websocket/filters
Content-Type: application/json
Authorization: Bearer YOUR_JWT_TOKEN

{
  "default_action": "block",
  "rules": [
    {
      "name": "High Severity Only",
      "description": "只接收高危和严重告警",
      "priority": 1,
      "enabled": true,
      "min_severity": "high",
      "event_types": {
        "operator": "in",
        "values": ["malware", "ransomware", "trojan"],
        "case_sensitive": false
      },
      "enable_aggregation": true,
      "max_messages_per_minute": 30
    }
  ]
}
```

### 3. 监控和告警

**监控指标**:
- 健康评分 (0-100%)
- 连接指标 (活跃连接、总连接、连接失败)
- 消息指标 (发送/接收/过滤/队列)
- 性能指标 (平均/P50/P95/P99延迟)

**创建告警规则**:
```http
POST /api/v1/monitoring/alerts/rules
Content-Type: application/json
Authorization: Bearer YOUR_JWT_TOKEN

{
  "name": "High Latency Alert",
  "description": "P95延迟超过500ms时告警",
  "conditions": [
    {
      "metric_type": "p95_latency",
      "operator": "gte",
      "threshold": 500.0,
      "duration_seconds": 60
    }
  ],
  "require_all": true,
  "severity": "warning",
  "enabled": true,
  "channels": ["log", "webhook"],
  "channel_config": {
    "webhook": {
      "webhook_url": "https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
    }
  },
  "cooldown_seconds": 300
}
```

### 4. 性能优化

**消息压缩**:
- 自动压缩 >1KB 的消息
- gzip 压缩级别 6
- 平均压缩率 65%

**批量发送**:
- 最多 100 条消息/批
- 最大延迟 100ms
- 吞吐量提升 5-10x

**连接池**:
- 最多 1000 个连接
- 空闲连接 5 分钟超时
- 自动健康检查

---

## API 参考

### WebSocket 端点

#### 连接端点

```
ws://localhost:8000/api/v1/ws/alerts?token=JWT&channels=alerts,system
```

**查询参数**:
- `token` (必需): JWT 认证令牌
- `channels` (可选): 逗号分隔的通道列表

#### 消息格式

所有消息遵循统一格式：

```json
{
  "type": "alert | playbook_run | system | ping | pong",
  "data": { ... },
  "timestamp": "2026-02-26T10:00:00.000Z",
  "channel": "alerts | playbook_runs | system"
}
```

### REST API 端点

#### 监控相关

| 方法 | 端点 | 描述 |
|------|------|------|
| GET | `/api/v1/ws/monitoring/metrics` | 获取当前监控指标 |
| GET | `/api/v1/ws/monitoring/health` | 获取系统健康评分 |
| GET | `/api/v1/ws/monitoring/summary` | 获取监控摘要 |
| GET | `/api/v1/ws/compression/stats` | 获取压缩统计 |
| GET | `/api/v1/ws/batch/stats` | 获取批量统计 |
| GET | `/api/v1/ws/pool/stats` | 获取连接池统计 |

#### 过滤器相关

| 方法 | 端点 | 描述 |
|------|------|------|
| GET | `/api/v1/websocket/filters` | 获取用户过滤器 |
| PUT | `/api/v1/websocket/filters` | 设置过滤器 |
| DELETE | `/api/v1/websocket/filters` | 删除过滤器 |
| GET | `/api/v1/websocket/filters/stats` | 获取过滤统计 |
| POST | `/api/v1/websocket/filters/test` | 测试消息 |

#### 告警相关

| 方法 | 端点 | 描述 |
|------|------|------|
| POST | `/api/v1/monitoring/alerts/rules` | 创建告警规则 |
| GET | `/api/v1/monitoring/alerts/rules` | 列出告警规则 |
| GET | `/api/v1/monitoring/alerts/rules/{id}` | 获取告警规则 |
| PUT | `/api/v1/monitoring/alerts/rules/{id}` | 更新告警规则 |
| DELETE | `/api/v1/monitoring/alerts/rules/{id}` | 删除告警规则 |
| GET | `/api/v1/monitoring/alerts/history` | 获取告警历史 |
| POST | `/api/v1/monitoring/alerts/test/{id}` | 测试告警规则 |

---

## 配置指南

### 环境变量

```bash
# WebSocket 配置
WS_COMPRESSION_ENABLED=true
WS_COMPRESSION_MIN_SIZE=1024
WS_COMPRESSION_LEVEL=6

WS_BATCH_ENABLED=true
WS_BATCH_MAX_SIZE=100
WS_BATCH_MAX_DELAY_MS=100

WS_POOL_ENABLED=true
WS_POOL_MAX_SIZE=1000
WS_POOL_MAX_IDLE_SECONDS=300

# 消息队列配置
REDIS_URL=redis://localhost:6379/0
MESSAGE_QUEUE_TTL=86400
MESSAGE_QUEUE_MAX_SIZE=1000
```

### 场景配置

#### 低延迟场景（实时告警）

```python
# 禁用批量，低压缩阈值
CompressionConfig(min_size_bytes=4096)
BatchConfig(enabled=False)
PoolConfig(max_idle_time_seconds=60)
```

#### 高吞吐场景（历史数据）

```python
# 高压缩率，大批量
CompressionConfig(min_size_bytes=512, compression_level=9)
BatchConfig(max_batch_size=200, max_batch_delay_ms=200)
PoolConfig(max_pool_size=5000, max_idle_time_seconds=600)
```

#### 平衡配置（推荐）

```python
# 默认配置
CompressionConfig(min_size_bytes=1024, compression_level=6)
BatchConfig(max_batch_size=100, max_batch_delay_ms=100)
PoolConfig(max_pool_size=1000, max_idle_time_seconds=300)
```

---

## 最佳实践

### 1. 连接管理

✅ **DO**:
- 在应用启动时建立连接
- 实现自动重连机制
- 监听连接状态变化
- 优雅关闭连接

❌ **DON'T**:
- 为每个用户创建多个连接
- 频繁连接/断开
- 忽略连接错误
- 阻塞主线程

### 2. 消息处理

✅ **DO**:
- 使用异步处理消息
- 批量处理相似消息
- 过滤不需要的消息
- 记录消息处理错误

❌ **DON'T**:
- 阻塞 WebSocket 线程
- 在消息处理中执行耗时操作
- 忽略消息验证
- 重复处理消息

### 3. 过滤器配置

✅ **DO**:
- 使用过滤器减少客户端负载
- 配置合理的优先级
- 定期审查过滤规则
- 监控过滤统计

❌ **DON'T**:
- 创建过多过滤规则（>20条）
- 使用过于复杂的正则表达式
- 忘记禁用不需要的规则
- 忽略过滤性能影响

### 4. 告警配置

✅ **DO**:
- 设置合理的阈值
- 配置冷却时间
- 使用多个通知渠道
- 定期测试告警规则

❌ **DON'T**:
- 设置过低的阈值（告警疲劳）
- 忽略告警严重性分级
- 配置重复的告警
- 忘记更新告警配置

---

## 故障排除

### 常见问题

#### 1. 连接失败

**症状**: WebSocket 连接立即断开

**可能原因**:
- JWT 令牌无效或过期
- CORS 配置错误
- 服务器未启动

**解决方案**:
```javascript
// 检查令牌
const token = localStorage.getItem('token');
if (!token) {
  console.error('No authentication token');
}

// 检查连接 URL
const wsUrl = `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/api/v1/ws/alerts?token=${token}`;

// 添加错误处理
ws.onerror = (error) => {
  console.error('WebSocket error:', error);
  // 尝试重新连接
  setTimeout(() => reconnect(), 5000);
};
```

#### 2. 消息未接收

**症状**: 已连接但未收到消息

**可能原因**:
- 未订阅正确的通道
- 过滤器阻止了消息
- 客户端消息处理错误

**解决方案**:
```javascript
// 检查订阅
ws.send(JSON.stringify({
  type: 'subscribe',
  channels: ['alerts', 'playbook_runs', 'system']
}));

// 检查过滤器
fetch('/api/v1/websocket/filters', {
  headers: { 'Authorization': `Bearer ${token}` }
})
.then(res => res.json())
.then(filters => {
  console.log('Current filters:', filters);
});

// 添加调试日志
ws.onmessage = (event) => {
  console.log('Message received:', event.data);
  // ... 处理消息
};
```

#### 3. 性能问题

**症状**: 高延迟或低吞吐量

**可能原因**:
- 消息过大
- 过多的并发连接
- CPU 或内存限制

**解决方案**:
```python
# 检查监控指标
GET /api/v1/ws/monitoring/metrics

# 调整配置
CompressionConfig(min_size_bytes=2048)  # 提高压缩阈值
BatchConfig(max_batch_size=50)           # 减少批量大小
PoolConfig(max_pool_size=500)            # 减少连接池大小
```

#### 4. 内存泄漏

**症状**: 内存使用持续增长

**可能原因**:
- 未释放的连接
- 消息队列积累
- 监控数据未清理

**解决方案**:
```python
# 定期清理
- 关闭空闲连接
- 清理过期消息队列
- 重置统计计数器
- 重启服务（如果需要）
```

---

## 相关文档

- [性能优化指南](./performance_guide.md)
- [部署指南](./websocket_deployment.md)
- [API 端点参考](../02-api-overview.md)
- [Week 3 总结报告](./week3/WEEK3_SUMMARY.md)

---

**文档版本**: v1.0.0
**最后更新**: 2026-02-26
