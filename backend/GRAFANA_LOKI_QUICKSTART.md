# Grafana + Loki 作为 Wazuh 替代方案 - 快速开始

**状态**: ✅ 已安装并运行  
**时间**: 2026-02-26

---

## 🎯 为什么选择 Grafana + Loki？

| 特性 | 说明 |
|------|------|
| ✅ **ARM64 原生支持** | 完美支持 Apple Silicon |
| ✅ **轻量级** | 资源占用少，启动快 |
| ✅ **强大告警** | 内置告警系统，支持多通道 |
| ✅ **易于集成** | REST API，易于对接 SOC Copilot |
| ✅ **免费开源** | 完全免费，社区活跃 |

---

## 🚀 快速开始

### 1. 访问 Grafana

```
URL: http://localhost:3001
用户名: admin
密码: admin
```

### 2. 添加 Loki 数据源

1. 登录 Grafana
2. 左侧菜单 → **Configuration** → **Data sources**
3. **Add data source** → 选择 **Loki**
4. 配置:
   - Name: `Loki`
   - URL: `http://loki:3100`
5. 点击 **Save & Test**

### 3. 查看日志

1. 左侧菜单 → **Explore**
2. 选择数据源: `Loki`
3. 标签过滤器: `{job="soc-copilot"}`
4. 点击 **Run query**

---

## 📊 集成到 SOC Copilot

### 方式 1: 发送告警到 Loki

Backend 可以发送结构化日志到 Loki：

```python
import requests

LOKI_URL = "http://localhost:3100/loki/api/v1/push"

def send_alert_to_loki(alert):
    """发送告警到 Loki"""
    payload = {
        "streams": [
            {
                "stream": {
                    "job": "soc-copilot",
                    "level": alert["severity"],
                    "event_type": alert["event_type"]
                },
                "values": [
                    [
                        str(int(datetime.now().timestamp() * 1000000000)),
                        json.dumps(alert)
                    ]
                ]
            }
        ]
    }
    
    requests.post(LOKI_URL, json=payload)
```

### 方式 2: Grafana 告警通知到 SOC Copilot

配置 Grafana 告警后通过 Webhook 通知：

1. **创建告警规则**
   - 左侧菜单 → **Alerting** → **New alert rule**
   - 设置查询条件
   - 配置通知

2. **配置 Webhook**
   ```
   URL: http://backend:8000/api/v1/webhooks/grafana
   Method: POST
   ```

3. **Backend 接收 Webhook**
   ```python
   @router.post("/webhooks/grafana")
   async def grafana_webhook(alert: dict):
       # 处理 Grafana 告警
       await websocket_manager.broadcast(alert)
       return {"status": "received"}
   ```

---

## 🔧 配置 SOC Copilot Backend

### 1. 更新 backend/.env

```bash
# Grafana + Loki 配置
GRAFANA_URL=http://localhost:3001
LOKI_URL=http://localhost:3100
PROMETHEUS_URL=http://localhost:9090

# 启用日志发送到 Loki
LOKI_ENABLED=true
LOKI_PUSH_URL=http://localhost:3100/loki/api/v1/push
```

### 2. 创建 Loki 客户端服务

```python
# backend/services/loki_client.py

import httpx
from datetime import datetime
from core.logger import get_logger

logger = get_logger(__name__)

class LokiClient:
    """Loki 日志发送客户端"""
    
    def __init__(self, push_url: str):
        self.push_url = push_url
        self.client = httpx.AsyncClient()
    
    async def send_alert(self, alert: dict):
        """发送告警到 Loki"""
        try:
            payload = {
                "streams": [
                    {
                        "stream": {
                            "job": "soc-copilot",
                            "level": alert.get("severity", "info"),
                            "event_type": alert.get("event_type", "unknown")
                        },
                        "values": [
                            [
                                str(int(datetime.now().timestamp() * 1000000000)),
                                json.dumps(alert)
                            ]
                        ]
                    }
                ]
            }
            
            response = await self.client.post(
                self.push_url,
                json=payload,
                timeout=5.0
            )
            
            if response.status_code == 204:
                logger.info(f"Alert sent to Loki: {alert.get('id')}")
            else:
                logger.error(f"Failed to send to Loki: {response.status_code}")
                
        except Exception as e:
            logger.error(f"Error sending to Loki: {e}")
```

---

## 📈 创建 Grafana 仪表板

### 1. 导入仪表板

1. **Dashboard** → **Import**
2. 使用仪表板 ID: `12272` (Loki 官方仪表板)
3. 或者创建自定义仪表板

### 2. 常用查询

```
# 所有错误日志
{job="soc-copilot", level="critical"} |= ``

# SSH 暴力破解
{job="soc-copilot", event_type="ssh_bruteforce"}

# 高危告警
{job="soc-copilot", level="high"} | json

# 时间范围统计
count_over_time({job="soc-copilot"}[5m])
```

### 3. 创建告警

```
# 告警条件: 5分钟内超过10个高危告警
count_over_time({job="soc-copilot", level="high"}[5m]) > 10
```

---

## 🎨 示例仪表板配置

### 安全告警概览

```json
{
  "title": "SOC Copilot 告警仪表板",
  "panels": [
    {
      "title": "告警总数",
      "targets": [
        {
          "expr": "count_over_time({job=\"soc-copilot\"}[1h])"
        }
      ]
    },
    {
      "title": "高危告警趋势",
      "targets": [
        {
          "expr": "count_over_time({job=\"soc-copilot\", level=\"high\"}[5m])"
        }
      ]
    },
    {
      "title": "告警类型分布",
      "targets": [
        {
          "expr": "count by (event_type) ({job=\"soc-copilot\"})"
        }
      ]
    }
  ]
}
```

---

## 🔗 集成测试

### 测试 Loki 连接

```bash
# 发送测试日志
curl -X POST http://localhost:3100/loki/api/v1/push \
  -H 'Content-Type: application/json' \
  -d '{
    "streams": [
      {
        "stream": {
          "job": "test",
          "level": "info"
        },
        "values": [
          [
            "'$(date +%s)000000000'",
            "Test log message"
          ]
        ]
      }
    ]
  }'
```

### 查询测试日志

```bash
# 查询日志
curl -G "http://localhost:3100/loki/api/v1/query" \
  --data-urlencode 'query={job="test"}'
```

---

## 📋 与 Wazuh 对比

| 功能 | Wazuh | Grafana + Loki |
|------|-------|----------------|
| **日志收集** | ✅ | ✅ |
| **告警** | ✅ | ✅ |
| **可视化** | ✅ | ✅ (更强大) |
| **SIEM 功能** | ✅ | ⚠️ (需要配置) |
| **ARM64 支持** | ❌ | ✅ |
| **资源占用** | 高 | 低 |
| **学习曲线** | 陡峭 | 平缓 |

---

## 🎯 下一步

### 立即可做：
1. ✅ 访问 Grafana: http://localhost:3001
2. ✅ 添加 Loki 数据源
3. ✅ 查看日志: Explore → Loki

### 集成到 SOC Copilot：
1. Backend 发送告警到 Loki
2. 配置 Grafana 告警规则
3. Webhook 通知回 SOC Copilot

### 高级功能：
1. 创建自定义仪表板
2. 配置告警通知通道
3. 集成 Prometheus 指标

---

## 🛠️ 常用命令

```bash
# 查看服务状态
docker compose -f docker-compose.grafana.yml ps

# 查看日志
docker compose -f docker-compose.grafana.yml logs -f grafana

# 重启服务
docker compose -f docker-compose.grafana.yml restart

# 停止服务
docker compose -f docker-compose.grafana.yml down
```

---

## 📚 相关资源

- **Grafana 文档**: https://grafana.com/docs/
- **Loki 文档**: https://grafana.com/docs/loki/latest/
- **Grafana Dashboards**: https://grafana.com/grafana/dashboards/

---

**状态**: ✅ 运行中  
**Grafana**: http://localhost:3001  
**Loki**: http://localhost:3100  
**Prometheus**: http://localhost:9090

需要帮助？查看故障排除指南或提交 issue。
