# WebSocket 性能优化指南

**版本**: v0.9.2
**更新日期**: 2026-02-26

---

## 目录

1. [性能优化概述](#性能优化概述)
2. [消息压缩](#消息压缩)
3. [批量发送](#批量发送)
4. [连接池](#连接池)
5. [监控和调优](#监控和调优)
6. [性能基准](#性能基准)
7. [故障排除](#故障排除)

---

## 性能优化概述

Week 3 引入了三项主要性能优化：

1. **消息压缩** - gzip 压缩减少 20-40% 网络流量
2. **批量发送** - 5-10x 吞吐量提升
3. **连接池** - 30% 连接开销减少

### 性能提升总结

| 指标     | 优化前    | 优化后       | 提升     |
| -------- | --------- | ------------ | -------- |
| 网络带宽 | 100%      | 60-80%       | 20-40% ↓ |
| 吞吐量   | 200 msg/s | 1,700+ msg/s | 8.5x ↑   |
| 连接开销 | 100%      | 70%          | 30% ↓    |
| P95 延迟 | 50ms      | 85ms         | +70%     |

---

## 消息压缩

### 工作原理

消息压缩使用 gzip 算法压缩大于阈值的消息：

```
原始消息 (4KB) → gzip 压缩 → 压缩消息 (1.3KB) → 网络传输
```

### 配置选项

```python
CompressionConfig(
    enabled=True,                    # 启用压缩
    min_size_bytes=1024,              # 只压缩 >1KB 的消息
    compression_level=6,              # 压缩级别 (0-9)
    max_compression_ratio=0.9         # 跳过压缩率 <10% 的消息
)
```

### 压缩级别对比

| 级别 | 压缩率 | 时间 | 用途         |
| ---- | ------ | ---- | ------------ |
| 1    | 60%    | 最快 | 实时消息     |
| 3    | 68%    | 快   | 低延迟场景   |
| 6    | 72%    | 中等 | 平衡（推荐） |
| 9    | 75%    | 最慢 | 归档数据     |

### 使用建议

**启用压缩的场景**:

- ✅ 消息大小 > 1KB
- ✅ 带宽受限环境
- ✅ 历史数据传输

**禁用压缩的场景**:

- ❌ 消息大小 < 512B
- ❌ 极低延迟要求（<10ms）
- ❌ CPU 资源受限

### 性能影响

**CPU 使用**: +15-20%
**延迟增加**: +5-10ms (平均)
**带宽节省**: 30-40%

---

## 批量发送

### 工作原理

批量发送将多个消息累积到一个批次中，然后一次性发送：

```
消息1 → 批次队列 → 消息2 → 批次队列 → 消息3 → 批次队列 → [触发条件] → 批量发送
```

### 配置选项

```python
BatchConfig(
    enabled=True,                     # 启用批量
    max_batch_size=100,               # 每批最多100条
    max_batch_delay_ms=100,           # 最多等待100ms
    min_batch_size=5                  # 至少5条才发送
)
```

### 触发条件

批量发送在以下情况下触发：

1. 批次达到 `max_batch_size`
2. 批次达到 `min_batch_size` 且等待时间超过 `max_batch_delay_ms`
3. 手动调用刷新 API

### 性能对比

| 场景        | 逐条发送 | 批量发送 | 提升 |
| ----------- | -------- | -------- | ---- |
| 10 条消息   | 50ms     | 15ms     | 3.3x |
| 100 条消息  | 500ms    | 55ms     | 9.1x |
| 1000 条消息 | 5000ms   | 520ms    | 9.6x |

### 使用建议

**启用批量的场景**:

- ✅ 高频消息（>100 msg/s）
- ✅ 历史数据查询
- ✅ 批量告警推送
- ✅ 日志流

**禁用批量的场景**:

- ❌ 实时告警（要求 <100ms 延迟）
- ❌ 用户交互响应
- ❌ 单条重要消息

### 权衡考虑

**优势**:

- 5-10x 吞吐量提升
- 减少网络往返
- 降低 CPU 使用

**劣势**:

- 增加消息延迟（最多 batch_delay）
- 需要额外内存缓存
- 顺序保证复杂度增加

---

## 连接池

### 工作原理

连接池管理 WebSocket 连接的生命周期：

```
新建连接 → 活跃池 → 空闲池 → 健康检查 → 复用/关闭
```

### 配置选项

```python
PoolConfig(
    enabled=True,                        # 启用连接池
    max_pool_size=1000,                  # 最大连接数
    max_idle_time_seconds=300,           # 5分钟空闲超时
    health_check_interval_seconds=60     # 健康检查间隔
)
```

### 连接状态

| 状态      | 描述   | 行为       |
| --------- | ------ | ---------- |
| ACTIVE    | 使用中 | 可发送消息 |
| IDLE      | 空闲   | 可复用     |
| UNHEALTHY | 不健康 | 将被关闭   |
| CLOSED    | 已关闭 | 将被移除   |

### 性能影响

**内存使用**: ~5KB/连接
**连接复用率**: 30-50%
**开销减少**: 30%

### 使用建议

**启用连接池的场景**:

- ✅ 高并发（>100 连接）
- ✅ 频繁重连
- ✅ 长连接场景

**禁用连接池的场景**:

- ❌ 低并发（<10 连接）
- ❌ 短连接场景
- ❌ 内存受限环境

---

## 监控和调优

### 关键指标

**压缩指标**:

```http
GET /api/v1/ws/compression/stats

{
  "total_messages": 10000,
  "compressed_messages": 8000,
  "compression_ratio": 0.65,
  "bytes_saved": 5200000
}
```

**批量指标**:

```http
GET /api/v1/ws/batch/stats

{
  "total_batches": 100,
  "total_messages_batched": 8500,
  "avg_batch_size": 85.0
}
```

**连接池指标**:

```http
GET /api/v1/ws/pool/stats

{
  "total_connections": 500,
  "active_connections": 350,
  "idle_connections": 150,
  "unhealthy_connections": 0
}
```

### 性能调优流程

1. **建立基准**
   - 运行性能测试
   - 记录基准指标
   - 识别瓶颈

2. **配置优化**
   - 调整压缩阈值
   - 优化批量大小
   - 调整连接池大小

3. **验证效果**
   - 运行相同测试
   - 对比指标
   - 确认提升

4. **持续监控**
   - 部署到生产
   - 监控指标
   - 定期审查

### 调优示例

**场景 1: 高延迟优化**

```python
# 问题: P95 延迟 > 200ms
# 原因: 批量延迟过高
# 解决: 减少批量延迟

BatchConfig(
    max_batch_size=50,        # 减少批量大小
    max_batch_delay_ms=50,    # 减少延迟
    min_batch_size=10
)
# 结果: P95 延迟降至 90ms
```

**场景 2: 内存优化**

```python
# 问题: 内存使用过高
# 原因: 连接池过大
# 解决: 限制连接池大小

PoolConfig(
    max_pool_size=500,              # 减少池大小
    max_idle_time_seconds=180,       # 更短超时
    health_check_interval_seconds=30  # 更频繁检查
)
# 结果: 内存使用减少 40%
```

**场景 3: CPU 优化**

```python
# 问题: CPU 使用率过高
# 原因: 压缩级别过高
# 解决: 降低压缩级别

CompressionConfig(
    min_size_bytes=2048,    # 提高阈值
    compression_level=3      # 降低级别
)
# 结果: CPU 使用降低 15%
```

---

## 性能基准

### 目标性能

| 指标            | 目标        | 实际        | 状态 |
| --------------- | ----------- | ----------- | ---- |
| 压缩 P95 时间   | < 50ms      | 9.8ms       | ✅   |
| 序列化 P95 时间 | < 5ms       | 2.65ms      | ✅   |
| 连接添加时间    | < 500ms     | 0.85ms      | ✅   |
| 批量吞吐量      | > 100 msg/s | 1,724 msg/s | ✅   |
| 健康检查开销    | < 10% CPU   | < 1% CPU    | ✅   |
| 网络带宽节省    | > 20%       | 30-40%      | ✅   |

### 硬件要求

**最低配置**:

- CPU: 2 cores
- 内存: 2 GB
- 网络: 100 Mbps

**推荐配置**:

- CPU: 4+ cores
- 内存: 4 GB
- 网络: 1 Gbps

**大规模部署**:

- CPU: 8+ cores
- 内存: 8 GB
- 网络: 10 Gbps
- Redis: 专用实例

### 容量规划

| 并发连接 | 推荐配置     | 预期吞吐量   |
| -------- | ------------ | ------------ |
| < 100    | 2 cores, 2GB | 500 msg/s    |
| 100-500  | 4 cores, 4GB | 1,500 msg/s  |
| 500-1000 | 8 cores, 8GB | 3,000 msg/s  |
| > 1000   | 集群部署     | 5,000+ msg/s |

---

## 故障排除

### 性能问题诊断

#### 问题 1: 高延迟

**症状**: 消息延迟 > 200ms

**诊断步骤**:

1. 检查批量配置
2. 查看监控指标
3. 分析网络延迟
4. 检查 CPU 使用

**解决方案**:

```python
# 减少批量延迟
BatchConfig(max_batch_delay_ms=50)

# 或禁用批量
BatchConfig(enabled=False)
```

#### 问题 2: 低吞吐量

**症状**: 吞吐量 < 500 msg/s

**诊断步骤**:

1. 检查网络带宽
2. 查看连接数
3. 分析消息大小
4. 检查 CPU 性能

**解决方案**:

```python
# 增加批量大小
BatchConfig(max_batch_size=200, max_batch_delay_ms=200)

# 启用压缩
CompressionConfig(min_size_bytes=512)
```

#### 问题 3: 高内存使用

**症状**: 内存使用 > 4GB

**诊断步骤**:

1. 检查连接池大小
2. 查看消息队列
3. 分析内存泄漏
4. 检查监控数据

**解决方案**:

```python
# 减少连接池
PoolConfig(max_pool_size=500, max_idle_time_seconds=180)

# 清理消息队列
await message_queue.clear_queue(user_id)
```

#### 问题 4: 高 CPU 使用

**症状**: CPU 使用 > 80%

**诊断步骤**:

1. 检查压缩级别
2. 查看健康检查频率
3. 分析监控开销
4. 检查消息处理

**解决方案**:

```python
# 降低压缩级别
CompressionConfig(compression_level=3)

# 减少健康检查
PoolConfig(health_check_interval_seconds=120)

# 禁用监控（如果不需要）
# monitoring_service.stop()
```

### 性能监控

**实时监控**:

```python
# 获取当前指标
metrics = await monitoring.get_current_metrics()

print(f"健康评分: {metrics.health_score}%")
print(f"P95 延迟: {metrics.performance.p95_latency_ms}ms")
print(f"吞吐量: {metrics.message.current_send_rate} msg/s")
```

**告警设置**:

```python
# 创建 P95 延迟告警
AlertRule(
    name="High P95 Latency",
    conditions=[
        AlertCondition(
            metric_type="p95_latency",
            operator="gte",
            threshold=200.0
        )
    ],
    severity="warning"
)
```

---

## 相关文档

- [WebSocket 功能指南](./websocket_guide.md)
- [部署指南](./websocket_deployment.md)
- [性能测试报告](./week3/PERFORMANCE_REPORT.md)

---

**文档版本**: v1.0.0
**最后更新**: 2026-02-26
