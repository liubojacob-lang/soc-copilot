# 🎯 下一步行动计划 - Grafana + Loki 集成

## ✅ 当前状态
- ✅ Grafana 运行正常 (http://localhost:3001)
- ✅ Loki 运行正常 (http://localhost:3100)
- ✅ 测试告警已发送
- ✅ 可以在 Grafana 中查看日志

---

## 🚀 下一步 - 3 个方向

### 方向 A: 完善集成（推荐）⭐⭐⭐⭐⭐
将 Grafana + Loki 集成到 SOC Copilot 的 Wazuh 页面

### 方向 B: 配置告警和仪表板
创建自定义仪表板和告警规则

### 方向 C: 生产化部署
配置持久化、备份、监控

---

## 🎯 方向 A: 完善集成（推荐）

### 目标
让 SOC Copilot 的 Wazuh 页面显示来自 Loki 的实时告警

### 步骤

#### 步骤 1: 配置 Backend 自动发送告警到 Loki

```python
# 在 backend/services/wazuh_stream_service.py 中集成 Loki

from services.loki_alert_sender import get_loki_sender

async def forward_alert_to_loki(alert_data):
    """将告警转发到 Loki"""
    loki_sender = get_loki_sender()
    await loki_sender.send_alert({
        "timestamp": datetime.utcnow().isoformat(),
        "event_type": alert_data.get("rule", "unknown"),
        "severity": alert_data.get("level", "info"),
        "agent_id": alert_data.get("agent", "system"),
        "source_ip": alert_data.get("src_ip", "unknown"),
        "description": alert_data.get("description", ""),
        "details": alert_data
    })
```

#### 步骤 2: 前端实时显示

在 Wazuh 页面中添加 Loki 数据源：

```typescript
// frontend/app/[locale]/wazuh/page.tsx

// 1. 从 Grafana Loki 查询日志
async function fetchAlertsFromLoki() {
  const response = await fetch(
    'http://localhost:3100/loki/api/v1/query_range?' +
    new URLSearchParams({
      query: '{job="soc-copilot"}',
      start: startTime,
      end: endTime,
      limit: '100'
    })
  );
  
  const data = await response.json();
  return data.data.result;
}

// 2. 实时更新（轮询或 WebSocket）
setInterval(() => {
  fetchAlertsFromLoki().then(alerts => {
    updateAlertsDisplay(alerts);
  });
}, 5000); // 每 5 秒刷新
```

#### 步骤 3: 测试完整流程

```bash
# 1. 启动后端（如果未启动）
cd backend && python main.py

# 2. 发送测试告警到 Wazuh stream
curl -X POST http://localhost:8000/api/v1/wazuh/stream/start \
  -H "Authorization: Bearer YOUR_TOKEN"

curl -X POST http://localhost:8000/api/v1/wazuh/stream/test-alert \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"agent_id": "001", "severity": "high", "count": 3}'

# 3. 打开 Wazuh 页面
# http://localhost:3003/zh/wazuh
# 应该能看到实时告警
```

---

## 📊 方向 B: 配置告警和仪表板

### 目标
创建专业的安全监控仪表板和告警规则

### 步骤

#### 步骤 1: 导入 SOC Copilot 仪表板

```
1. Grafana → Dashboard → Import
2. Upload JSON file: grafana-soc-dashboard.json
3. 选择 Loki 数据源
4. 点击 Import
```

**预期仪表板包含**:
- 告警总数统计
- 严重级别趋势图
- 告警类型分布饼图
- 最新告警列表
- Top 源 IP 表格
- Top 攻击类型柱状图

#### 步骤 2: 创建告警规则

```
1. Alerting → New alert rule
2. 设置名称: 高危告警激增
3. 查询条件:
   count_over_time({job="soc-copilot", level="critical"}[5m]) > 0
4. 设置通知: Webhook / Email
5. 保存告警规则
```

#### 步骤 3: 配置通知渠道

```yaml
# Webhook 配置
URL: http://backend:8000/api/v1/webhooks/grafana-alert
Method: POST

# 通知内容
{
  "alert_name": "高危告警检测",
  "severity": "critical",
  "message": "检测到严重安全告警",
  "logs": "..."
}
```

---

## 🔧 方向 C: 生产化部署

### 目标
配置生产环境所需的功能

### 步骤

#### 步骤 1: 数据持久化

```yaml
# docker-compose.grafana.yml 中已配置
volumes:
  grafana-data:  # 仪表板配置
  prometheus-data:  # 指标数据
```

#### 步骤 2: 配置自动启动

```bash
# 创建 systemd 服务或使用 Docker restart policy
# docker-compose.grafana.yml 中已设置:
restart: unless-stopped
```

#### 步骤 3: 数据备份

```bash
# 备份 Grafana 配置
docker exec grafana grafana-cli admin dashboards export > backup.json

# 备份 Prometheus 数据
docker exec prometheus promtool tsdb create-blocks-from open --help
```

---

## 💡 推荐行动路线

### 今天（1 小时内）

#### 选项 1: 快速体验（推荐）
```
1. ✅ 发送更多测试告警
2. ✅ 探索 Grafana 功能
3. ✅ 测试标签过滤
4. ✅ 查看不同视图模式
```

#### 选项 2: 仪表板配置
```
1. ✅ 导入 grafana-soc-dashboard.json
2. ✅ 自定义面板
3. ✅ 配置自动刷新
```

#### 选项 3: 告警测试
```
1. ✅ 创建告警规则
2. ✅ 测试告警触发
3. ✅ 配置通知方式
```

### 本周（5 小时）

#### 1. 完善 Backend 集成
```python
# 实现自动告警转发
# 每次 Wazuh stream 收到告警时，自动发送到 Loki
```

#### 2. 前端实时显示
```typescript
// 在 Wazuh 页面添加 Loki 数据源
// 实现实时告警显示
```

#### 3. 创建自动化流程
```bash
# 定时任务：每小时汇总告警
# 告警聚合：合并相似告警
# 趋势分析：生成告警趋势报告
```

### 下月（20 小时）

#### 1. 高级功能
- 机器学习异常检测
- 自动响应规则
- 报表系统
- 多租户支持

#### 2. 集成扩展
- 更多数据源（系统日志、应用日志）
- SIEM 关联分析
- 威胁情报集成

#### 3. 优化
- 性能调优
- 资源优化
- 监控和告警

---

## 🎯 立即可以做的事情

### 选项 1: 探索 Grafana 功能（5 分钟）

```
1. 切换到 Table 视图查看表格形式
2. 切换到 Time Series 视图查看趋势
3. 使用标签过滤器筛选特定级别
4. 点击日志展开查看完整 JSON
5. 测试搜索功能：在日志中搜索关键词
```

### 选项 2: 创建自定义查询（10 分钟）

```
1. 查询特定级别: {job="soc-copilot", level="critical"}
2. 查询特定类型: {job="soc-copilot", event_type="ssh_bruteforce"}
3. 组合查询: {job="soc-copilot"} |= "attack"
4. 聚合查询: count_over_time({job="soc-copilot"}[5m])
```

### 选项 3: 发送更多测试数据（5 分钟）

```bash
# 发送大量测试告警
for i in {1..10}; do
  curl -X POST http://localhost:3100/loki/api/v1/push \
    -H 'Content-Type: application/json' \
    -d '{
      "streams": [{
        "stream": {
          "job": "soc-copilot",
          "level": "info",
          "test_id": "'$i'"
        },
        "values": [
          ["'$(date +%s)000000000'", "{\"test\": '$i'}"]
        ]
      }]
    }'
  sleep 1
done
```

---

## 📋 行动建议

### 如果您想快速看到效果
→ **选择方向 A**: 集成到 Wazuh 页面

### 如果您想深入配置
→ **选择方向 B**: 配置仪表板和告警

### 如果您想准备生产环境
→ **选择方向 C**: 生产化部署

---

## 🤔 需要我帮您做什么？

请告诉我您想：

1. **集成到前端** - 我可以修改前端代码
2. **创建自动化流程** - 我可以编写脚本
3. **配置告警规则** - 我可以提供详细配置
4. **优化性能** - 我可以调优配置
5. **其他需求** - 请具体说明

---

## 🎓 学习资源

### 官方文档
- [Grafana 文档](https://grafana.com/docs/)
- [Loki 查询语言](https://grafana.com/docs/loki/latest/logql/)
- [Grafana 仪表板](https://grafana.com/docs/grafana/latest/dashboards/)

### 本地文档
- `COMPLETE_INTEGRATION_GUIDE.md` - 完整集成指南
- `GRAFANA_EXPECTED_RESULTS.md` - 预期结果
- `GRAFANA_VISUAL_GUIDE.md` - 可视化指南

---

## ✅ 总结

您现在已经拥有：
- ✅ 运行中的 Grafana + Loki 栈
- ✅ 测试告警已发送并验证
- ✅ 可以在 Grafana 中查看数据

下一步建议：
1. 🎯 **短期**: 探索 Grafana 功能，熟悉界面
2. 🎯 **中期**: 集成到 SOC Copilot 前端
3. 🎯 **长期**: 配置完整的告警和监控系统

---

**请告诉我您想从哪个方向开始？**

A. 集成到前端 Wazuh 页面
B. 创建自定义仪表板
C. 配置告警规则
D. 其他具体需求

我会立即开始帮您实现！🚀
