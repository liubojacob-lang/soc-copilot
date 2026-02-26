# Loki 使用指南

## ⚠️ 重要说明

**Loki 没有独立的 Web UI！**

Loki 是一个日志聚合系统，提供 API 接口。要查看日志，**必须通过 Grafana**。

---

## ✅ 验证 Loki 运行正常

### 检查健康状态

```bash
curl http://localhost:3100/ready
# 应该返回: ready
```

### 查看配置

```bash
curl http://localhost:3100/config
# 返回配置信息
```

### 测试推送日志

```bash
curl -X POST http://localhost:3100/loki/api/v1/push \
  -H 'Content-Type: application/json' \
  -d '{
    "streams": [
      {
        "stream": {"job": "test"},
        "values": [
          ["'$(date +%s)000000000'", "test message"]
        ]
      }
    ]
  }'
# 应该返回: 204 No Content
```

---

## 🎯 查看日志的正确方式

### 通过 Grafana（推荐）

1. **访问 Grafana**
   ```
   http://localhost:3001
   用户名: admin
   密码: admin
   ```

2. **配置 Loki 数据源**
   ```
   Configuration → Data sources → Add data source → Loki
   URL: http://loki:3100
   Save & Test
   ```

3. **查看日志**
   ```
   Explore → 选择 Loki → 查询: {job="soc-copilot"}
   Run query
   ```

### 通过 API

```bash
# 查询日志
curl -G "http://localhost:3100/loki/api/v1/query" \
  --data-urlencode 'query={job="soc-copilot"}' \
  --data-urlencode 'limit=10' | jq '.'
```

---

## 📊 Loki 架构

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  应用/脚本  │────→│    Loki    │────→│  Grafana   │
│             │ API │  (日志存储) │     │  (可视化)   │
└─────────────┘     └─────────────┘     └─────────────┘
```

- **Loki**: 只负责存储和提供 API
- **Grafana**: 负责可视化和查询界面
- **Promtail**: 负责收集日志

---

## 🔧 常用命令

### 发送日志到 Loki

```python
import requests
import time

def send_log_to_loki(message):
    payload = {
        "streams": [
            {
                "stream": {
                    "job": "my-app",
                    "level": "info"
                },
                "values": [
                    [str(int(time.time() * 1000000000)), message]
                ]
            }
        ]
    }
    
    response = requests.post(
        "http://localhost:3100/loki/api/v1/push",
        json=payload
    )
    
    return response.status_code == 204
```

### 查询日志

```bash
# 基本查询
curl -G "http://localhost:3100/loki/api/v1/query" \
  --data-urlencode 'query={job="soc-copilot"}'

# 时间范围查询
curl -G "http://localhost:3100/loki/api/v1/query_range" \
  --data-urlencode 'query={job="soc-copilot"}' \
  --data-urlencode 'start=1700000000000000000' \
  --data-urlencode 'end=1700000036000000000'

# 过滤查询
curl -G "http://localhost:3100/loki/api/v1/query" \
  --data-urlencode 'query={job="soc-copilot", level="critical"}'
```

---

## 📋 总结

| 访问方式 | URL | 说明 |
|---------|-----|------|
| **Loki API** | http://localhost:3100/* | 日志存储和查询 API |
| **Loki 根路径** | http://localhost:3100/ | ❌ 404 - 正常，无 UI |
| **Grafana 界面** | http://localhost:3001 | ✅ 查看日志的地方 |
| **健康检查** | http://localhost:3100/ready | ✅ 服务健康 |

---

**记住**：
- ✅ Loki = 纯 API 服务
- ✅ Grafana = 可视化界面
- ❌ 不要直接访问 http://localhost:3100/ 查看日志

**正确流程**：
发送日志 → Loki → 通过 Grafana 查询
