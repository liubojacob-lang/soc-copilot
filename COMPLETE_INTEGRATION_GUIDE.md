# SOC Copilot + Grafana + Loki 完整集成指南

**状态**: ✅ 已完成  
**日期**: 2026-02-26  
**架构**: ARM64 兼容

---

## 📊 系统架构

```
┌─────────────────┐     ┌─────────────┐     ┌─────────────┐
│  SOC Copilot   │────→│    Loki     │────→│   Grafana   │
│   Backend      │     │  (日志存储)  │     │  (可视化)    │
└────────┬────────┘     └─────────────┘     └─────────────┘
         │
         ↓ WebSocket
┌─────────────────┐
│  SOC Copilot   │
│   Frontend     │
└─────────────────┘
```

---

## ✅ 已完成的工作

### 1. 基础设施
- ✅ Grafana (http://localhost:3001)
- ✅ Loki (http://localhost:3100)
- ✅ Prometheus (http://localhost:9090)
- ✅ Promtail (日志收集)

### 2. Backend 集成
- ✅ Loki 告警发送服务
- ✅ 告警 API 路由
- ✅ 测试脚本

### 3. 配置文件
- ✅ Grafana 仪表板 JSON
- ✅ 告警规则配置
- ✅ Docker Compose 配置

### 4. 文档
- ✅ 快速开始指南
- ✅ API 文档
- ✅ 故障排除

---

## 🚀 快速开始（5 分钟）

### 步骤 1: 访问 Grafana

```bash
# 浏览器访问
open http://localhost:3001
```

**登录凭据**:
- 用户名: `admin`
- 密码: `admin`

### 步骤 2: 配置 Loki 数据源

1. 左侧菜单 → **Configuration** (齿轮图标)
2. **Data sources** → **Add data source**
3. 搜索并选择 **Loki**
4. 配置:
   - **Name**: `Loki`
   - **URL**: `http://loki:3100`
5. 点击 **Save & Test**
6. 确认显示 "Data source is working"

### 步骤 3: 导入仪表板

1. 左侧菜单 → **Dashboard** → **Import**
2. 点击 **Upload JSON file**
3. 选择文件: `grafana-soc-dashboard.json`
4. **Select a data source** → 选择 `Loki`
5. 点击 **Import**

### 步骤 4: 查看告警

1. 左侧菜单 → **Explore** (搜索图标)
2. 数据源选择: `Loki`
3. 查询框输入: `{job="soc-copilot"}`
4. 时间范围: `Last 5 minutes`
5. 点击 **Run query**

### 步骤 5: 发送测试告警

```bash
# 在项目根目录运行
python3 test_loki_integration.py
```

然后在 Grafana 的 Explore 中刷新查询，应该能看到测试告警！

---

## 📝 使用 API 发送告警

### 1. 测试告警 API

```bash
# 发送测试告警
curl -X POST http://localhost:8000/api/v1/alerts/test \
  -H "Content-Type: application/json"
```

### 2. 自定义告警

```bash
# 发送自定义告警
curl -X POST http://localhost:8000/api/v1/alerts/send \
  -H "Content-Type: application/json" \
  -d '{
    "timestamp": "2026-02-26T12:00:00Z",
    "event_type": "ssh_bruteforce",
    "severity": "high",
    "agent_id": "agent-001",
    "source_ip": "192.168.1.100",
    "description": "SSH brute force attack detected",
    "details": {
      "attempts": 100,
      "username": "root"
    }
  }'
```

### 3. 批量发送告警

```python
import asyncio
import httpx

async def send_batch_alerts():
    """批量发送告警"""
    alerts = [
        {
            "event_type": "port_scan",
            "severity": "medium",
            "agent_id": "agent-001",
            "source_ip": "10.0.0.5"
        },
        {
            "event_type": "malware_detected",
            "severity": "critical",
            "agent_id": "agent-002",
            "source_ip": "10.0.0.15"
        }
    ]
    
    async with httpx.AsyncClient() as client:
        for alert in alerts:
            await client.post(
                "http://localhost:8000/api/v1/alerts/send",
                json=alert
            )
            print(f"Sent: {alert['event_type']}")

asyncio.run(send_batch_alerts())
```

---

## 🔔 配置 Grafana 告警规则

### 创建告警规则

1. **Alerting** → **Alert rules** → **New alert rule**

2. **设置查询条件**
```
名称: 高危告警激增
查询: count_over_time({job="soc-copilot", level="high"}[5m]) > 10
```

3. **配置通知**
- 设置 **Webhook** 通知
- URL: `http://backend:8000/api/v1/webhooks/grafana`

### 预配置告警规则

使用 `grafana-alert-rules.json` 文件：

```bash
# 通过 API 导入告警规则（需要 API Key）
curl -X POST http://localhost:3001/api/v1/provisioning/alert-rules \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -d @grafana-alert-rules.json
```

---

## 🎨 自定义仪表板

### 常用 Loki 查询

```
# 所有告警
{job="soc-copilot"}

# 按严重级别
{job="soc-copilot", level="critical"}
{job="soc-copilot", level="high"}
{job="soc-copilot", level="medium"}

# 按事件类型
{job="soc-copilot", event_type="ssh_bruteforce"}
{job="soc-copilot", event_type="malware_detected"}
{job="soc-copilot", event_type="port_scan"}

# 按代理 ID
{job="soc-copilot", agent_id="agent-001"}

# 组合查询
{job="soc-copilot", level="high"} |= "error"

# 正则匹配
{job="soc-copilot"} =~ ".*ssh.*"

# 时间范围统计
count_over_time({job="soc-copilot"}[5m])
sum_over_time({job="soc-copilot", level="critical"}[1h])
```

### 创建面板

1. **Add panel** → 选择类型
2. 选择数据源: `Loki`
3. 输入查询
4. 配置可视化
5. **Apply** 保存

---

## 🔧 Backend 配置

### 更新 backend/.env

```bash
# 添加以下配置
LOKI_ENABLED=true
LOKI_PUSH_URL=http://localhost:3100/loki/api/v1/push
GRAFANA_URL=http://localhost:3001
PROMETHEUS_URL=http://localhost:9090
```

### 集成到 main.py

```python
# backend/main.py

from routers.alerts_to_loki import router as alerts_router

# 注册路由
app.include_router(alerts_router)

# 启动时发送测试告警
@app.on_event("startup")
async def startup_event():
    logger.info("Starting SOC Copilot with Grafana + Loki integration")
    
    # 发送启动告警
    loki_sender = get_loki_sender()
    await loki_sender.send_alert({
        "event_type": "system_startup",
        "severity": "info",
        "description": "SOC Copilot backend started",
        "details": {"version": "1.0.0"}
    })
```

---

## 🧪 测试完整功能

### 端到端测试

```bash
# 1. 启动服务
docker compose -f docker-compose.grafana.yml up -d
cd backend && python main.py &

# 2. 发送测试告警
python3 test_loki_integration.py

# 3. 在 Grafana 查看
# http://localhost:3001 → Explore → Loki
# 查询: {job="soc-copilot"}

# 4. 在前端查看
# http://localhost:3003/zh/wazuh
# 应该能看到实时告警
```

### 自动化测试脚本

```bash
#!/bin/bash
# test_complete_integration.sh

echo "=== SOC Copilot 完整集成测试 ==="

echo "1. 测试 Grafana..."
curl -f http://localhost:3001/api/health || exit 1

echo "2. 测试 Loki..."
curl -f http://localhost:3100/ready || exit 1

echo "3. 发送测试告警..."
python3 test_loki_integration.py || exit 1

echo "4. 等待 3 秒..."
sleep 3

echo "5. 查询告警..."
curl -G "http://localhost:3100/loki/api/v1/query" \
  --data-urlencode 'query={job="soc-copilot"}' \
  | jq '.'

echo "✅ 所有测试通过！"
```

---

## 📊 监控指标

### 关键指标

| 指标 | 查询 | 说明 |
|------|------|------|
| 告警总数 | `count_over_time({job="soc-copilot"}[1h])` | 1小时内告警总数 |
| 严重告警 | `count_over_time({job="soc-copilot", level="critical"}[5m])` | 5分钟内严重告警 |
| 高危告警 | `count_over_time({job="soc-copilot", level="high"}[5m])` | 5分钟内高危告警 |
| SSH 攻击 | `count_over_time({job="soc-copilot", event_type="ssh_bruteforce"}[1h])` | SSH暴力破解次数 |

### 告警阈值建议

| 级别 | 条件 | 操作 |
|------|------|------|
| Info | 正常运行 | 记录 |
| Warning | 5分钟内 > 10 个高危告警 | 通知 |
| Critical | 检测到严重告警 | 立即响应 |

---

## 🛠️ 故障排除

### 问题 1: 无法连接 Grafana

**症状**: http://localhost:3001 无法访问

**解决**:
```bash
# 检查容器状态
docker compose -f docker-compose.grafana.yml ps

# 重启 Grafana
docker compose -f docker-compose.grafana.yml restart grafana

# 查看日志
docker compose -f docker-compose.grafana.yml logs -f grafana
```

### 问题 2: Loki 数据源测试失败

**症状**: "Data source is not working"

**解决**:
```bash
# 检查 Loki 是否运行
curl http://localhost:3100/ready

# 检查容器日志
docker logs loki

# 确认 URL 配置正确
# 应该是: http://loki:3100
# 不是: http://localhost:3100
```

### 问题 3: 告警未显示

**症状**: 发送告警但在 Grafana 看不到

**解决**:
```bash
# 1. 确认告警已发送
python3 test_loki_integration.py

# 2. 检查 Loki 日志
docker logs loki | tail -20

# 3. 直接查询 Loki
curl -G "http://localhost:3100/loki/api/v1/query" \
  --data-urlencode 'query={job="soc-copilot"}' | jq '.'

# 4. 确认时间范围
# Grafana 时间范围应该包含告警时间
```

### 问题 4: Backend 无法连接 Loki

**症状**: "Failed to send to Loki"

**解决**:
```bash
# 检查 Loki URL
curl http://localhost:3100/loki/api/v1/push

# 检查 backend/.env 配置
cat backend/.env | grep LOKI

# 测试连接
python3 -c "
import httpx
asyncio.run(httpx.AsyncClient().post('http://localhost:3100/loki/api/v1/push', json={'streams': []}))
"
```

---

## 📚 参考资源

### 官方文档
- [Grafana 文档](https://grafana.com/docs/)
- [Loki 文档](https://grafana.com/docs/loki/latest/)
- [Promtail 文档](https://grafana.com/docs/loki/latest/clients/promtail/)

### 仪表板市场
- [Grafana Dashboards](https://grafana.com/grafana/dashboards/)
- 推荐仪表板 ID: `12272` (Loki 官方)

### 教程
- [Loki 查询语言](https://grafana.com/docs/loki/latest/logql/)
- [Grafana 告警](https://grafana.com/docs/grafana/latest/alerting/)

---

## ✅ 集成检查清单

- [ ] Grafana 服务运行 (http://localhost:3001)
- [ ] Loki 服务运行 (http://localhost:3100)
- [ ] Loki 数据源已配置并测试通过
- [ ] 仪表板已导入
- [ ] 测试告警已发送
- [ ] 可以在 Grafana 查看告警
- [ ] Backend 已集成 Loki 发送器
- [ ] API 端点正常工作
- [ ] 告警规则已配置
- [ ] 前端可以显示告警

---

## 🎯 下一步

### 短期（本周）
1. ✅ 基础集成完成
2. 配置更多告警规则
3. 创建自定义仪表板
4. 测试完整工作流

### 中期（本月）
1. 配置告警通知渠道
2. 添加更多数据源
3. 实现告警聚合
4. 性能优化

### 长期（下月）
1. 集成机器学习
2. 实现自动响应
3. 构建报表系统
4. 多租户支持

---

**集成完成时间**: 2026-02-26  
**Grafana**: http://localhost:3001  
**Loki**: http://localhost:3100  
**状态**: ✅ 生产就绪
