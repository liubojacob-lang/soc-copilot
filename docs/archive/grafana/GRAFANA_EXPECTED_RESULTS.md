# Grafana 测试告警 - 预期结果详解

## 📤 发送测试告警

### 命令
```bash
./send_test_alert.sh
```

### 预期返回（终端输出）

```
=== 发送测试告警到 Loki ===

1️⃣ 发送高危告警...
✅ 发送完成

2️⃣ 发送 SSH 暴力破解告警...
✅ 发送完成

3️⃣ 发送端口扫描告警...
✅ 发送完成

4️⃣ 发送信息日志...
✅ 发送完成

✅ 所有测试告警已发送！

现在在 Grafana 中查看：
  1. Explore → Loki 数据源
  2. 查询: {job="soc-copilot"}
  3. 时间范围: Last 5 minutes
  4. Run query
```

**HTTP 状态码**: 204 No Content（表示成功）

---

## 📊 Grafana 中的预期结果

### 1️⃣ Explore 页面布局

```
┌────────────────────────────────────────────────────┐
│ Grafana                       [Time: Last 5 minutes] │
├────────────────────────────────────────────────────┤
│                                                │ │
│  Query: [Loki ▼]                                 │ │
│         {job="soc-copilot"}                       │ │
│         [Run query]                     [Refresh] │ │
│                                                │ │
│  Labels:                                       │ │
│  ┌────────────────────────────────────┐        │ │
│  │ event_type  ▼                    │        │ │
│  │ agent_id    ▼                    │        │ │
│  │ level       ▼                    │        │ │
│  └────────────────────────────────────┘        │ │
│                                                │ │
│  ┌──────────────────────────────────────────┐  │ │
│  │ 📊 Results: 4 streams                  │  │ │
│  │                                          │  │ │
│  │ ▼ stream 1 (malware_detected)           │  │ │
│  │   Timestamp: 2026-02-26 11:30:15       │  │ │
│  │   Labels:                               │  │ │
│  │     job: soc-copilot                    │  │ │
│  │     level: critical                     │  │ │
│  │     event_type: malware_detected        │  │ │
│  │     agent_id: agent-001                 │  │ │
│  │     source_ip: 192.168.1.100           │  │ │
│  │   Log:                                  │  │ │
│  │     {"message": "Malware detected..."}  │  │ │
│  │                                          │  │ │
│  │ ▼ stream 2 (ssh_bruteforce)             │  │ │
│  │   Timestamp: 2026-02-26 11:30:16       │  │ │
│  │   Labels:                               │  │ │
│  │     level: high                         │  │ │
│  │     event_type: ssh_bruteforce          │  │ │
│  │     agent_id: agent-002                 │  │ │
│  │     source_ip: 10.0.0.5                │  │ │
│  │   Log:                                  │  │ │
│  │     {"message": "SSH brute force..."}  │  │ │
│  │                                          │  │ │
│  │ ▼ stream 3 (port_scan)                  │  │ │
│  │ ▼ stream 4 (system_info)                │  │ │
│  │                                          │  │ │
│  └──────────────────────────────────────────┘  │ │
└────────────────────────────────────────────────────┘
```

---

## 🔍 详细预期结果

### 结果概览

| 项目 | 预期值 |
|------|--------|
| **查询状态** | ✅ Success (绿色) |
| **返回流数量** | 4 streams |
| **总日志条数** | 4 entries |
| **时间范围** | Last 5 minutes |
| **数据源** | Loki |

---

### 📋 日志详情

#### 🚨 告警 1: 恶意软件检测（Critical）

**显示内容**:
```
Timestamp: 2026-02-26 11:30:15.123

Labels:
┌────────────────────────────────────┐
│ job          = soc-copilot         │
│ level        = critical            │
│ event_type   = malware_detected    │
│ agent_id     = agent-001           │
│ source_ip    = 192.168.1.100       │
│ service_name = soc-copilot         │
└────────────────────────────────────┘

Log Entry:
{
  "message": "Malware detected on host",
  "file": "trojan.exe",
  "action": "quarantined"
}
```

**颜色标识**: 🔴 红色（critical 级别）

---

#### ⚠️ 告警 2: SSH 暴力破解（High）

**显示内容**:
```
Timestamp: 2026-02-26 11:30:16.456

Labels:
┌────────────────────────────────────┐
│ job          = soc-copilot         │
│ level        = high                │
│ event_type   = ssh_bruteforce      │
│ agent_id     = agent-002           │
│ source_ip    = 10.0.0.5             │
└────────────────────────────────────┘

Log Entry:
{
  "message": "SSH brute force attack detected",
  "attempts": 100,
  "username": "root"
}
```

**颜色标识**: 🟠 橙色（high 级别）

---

#### 🔍 告警 3: 端口扫描（Medium）

**显示内容**:
```
Timestamp: 2026-02-26 11:30:17.789

Labels:
┌────────────────────────────────────┐
│ job          = soc-copilot         │
│ level        = medium              │
│ event_type   = port_scan           │
│ agent_id     = agent-003           │
│ source_ip    = 172.16.0.50         │
└────────────────────────────────────┘

Log Entry:
{
  "message": "Port scan detected",
  "scanned_ports": [22, 80, 443, 3306],
  "duration": "5s"
}
```

**颜色标识**: 🟡 黄色（medium 级别）

---

#### ℹ️ 告警 4: 系统信息（Info）

**显示内容**:
```
Timestamp: 2026-02-26 11:30:18.012

Labels:
┌────────────────────────────────────┐
│ job          = soc-copilot         │
│ level        = info                │
│ event_type   = system_info         │
│ agent_id     = system              │
│ source_ip    = 127.0.0.1           │
└────────────────────────────────────┘

Log Entry:
{
  "message": "System health check completed",
  "status": "healthy",
  "uptime": 3600
}
```

**颜色标识**: 🔵 蓝色（info 级别）

---

## 📊 视图展示

### Table 视图（表格模式）

| Timestamp | Level | Event Type | Agent ID | Source IP | Message |
|-----------|-------|------------|----------|-----------|---------|
| 11:30:15 | critical | malware_detected | agent-001 | 192.168.1.100 | Malware detected... |
| 11:30:16 | high | ssh_bruteforce | agent-002 | 10.0.0.5 | SSH brute force... |
| 11:30:17 | medium | port_scan | agent-003 | 172.16.0.50 | Port scan... |
| 11:30:18 | info | system_info | system | 127.0.0.1 | System health... |

---

### Logs 视图（日志模式）

```
┌──────────────────────────────────────────────────┐
│ 2026-02-26 11:30:15 │ critical │ malware_detected│
│ {"message": "Malware detected on host", ...}    │
├──────────────────────────────────────────────────┤
│ 2026-02-26 11:30:16 │ high     │ ssh_bruteforce  │
│ {"message": "SSH brute force attack", ...}      │
├──────────────────────────────────────────────────┤
│ 2026-02-26 11:30:17 │ medium   │ port_scan       │
│ {"message": "Port scan detected", ...}          │
├──────────────────────────────────────────────────┤
│ 2026-02-26 11:30:18 │ info     │ system_info     │
│ {"message": "System health check", ...}         │
└──────────────────────────────────────────────────┘
```

---

## 🎨 标签过滤功能

### 按严重级别过滤

在 Grafana 中可以看到标签过滤器：

```
event_type  ┌────────────────────┐
agent_id    │ malware_detected   │
level       │ ssh_bruteforce     │
            │ port_scan          │
            │ system_info        │
            └────────────────────┘

level:  ┌──────────┐
        │ critical │  ← 显示 1 条
        │ high     │  ← 显示 1 条
        │ medium   │  ← 显示 1 条
        │ info     │  ← 显示 1 条
        └──────────┘
```

**交互**: 点击标签值可以过滤只显示该级别的日志

---

## 🔍 时间序列视图

### 切换到 Time Series 视图

如果在查询中添加聚合函数：

```logql
count_over_time({job="soc-copilot"}[1m])
```

**预期图表**:
```
数量 │
  4  │      █
  3  │      █
  2  │      █
  1  │      █
  0  └──────┴──────
     11:30 11:31
```

**X轴**: 时间（分钟）  
**Y轴**: 日志数量  
**图例**: 显示每分钟的日志总数

---

## 📊 统计信息

### Grafana 查询统计

在查询结果下方可以看到：

```
Stats:
┌────────────────────────────────┐
│ Total entries:      4          │
│ Total streams:     4          │
│ Time range:        5 minutes  │
│ Query time:        < 100ms    │
└────────────────────────────────┘
```

---

## ✅ 验证成功的标志

### 必须看到的内容

1. ✅ **"Results: 4 streams"** 或类似提示
2. ✅ **4 条不同的日志条目**
3. ✅ **每条日志都有标签和内容**
4. ✅ **时间戳在最近 5 分钟内**
5. ✅ **JSON 格式的日志内容可以展开**

### 不应该看到

- ❌ "No data found"
- ❌ "Query returned no results"
- ❌ "Data source is not working"
- ❌ 空白的查询结果
- ❌ 超过 10 秒的查询时间

---

## 🎯 完整流程验证

### 步骤 1: 发送告警

```bash
./send_test_alert.sh
```

**预期**: 
```
✅ 所有测试告警已发送！
```

### 步骤 2: 在 Grafana 查询

1. Explore → Loki
2. 输入: `{job="soc-copilot"}`
3. 点击 Run query

**预期**: 立即显示 4 条日志

### 步骤 3: 验证内容

点击任意日志条目展开

**预期**: 
- 显示完整 JSON 内容
- 显示所有标签
- 时间戳正确

### 步骤 4: 测试过滤

点击某个 `level` 标签值（如 `critical`）

**预期**: 只显示该级别的日志

---

## 🛠️ 故障排除

### 如果看不到日志

#### 检查 1: Loki 是否收到数据

```bash
curl -G "http://localhost:3100/loki/api/v1/query_range" \
  --data-urlencode 'query={job="soc-copilot"}' \
  --data-urlencode 'start='$(date -v-5M +%s)000000000 \
  --data-urlencode 'end='$(date +%s)000000000 | jq '.data.result | length'
```

**预期**: 返回 `4`

#### 检查 2: Grafana 数据源配置

```
Configuration → Data sources → Loki
查看 "Last tested" 时间
点击 "Test" 按钮
```

**预期**: "Data source is working"

#### 检查 3: 时间范围

确认 Grafana 时间范围设置为：
- "Last 5 minutes"
- 或包含发送告警的时间范围

---

## 📝 快速对照表

| 步骤 | 操作 | 预期结果 | 状态 |
|------|------|----------|------|
| 1 | 发送测试告警 | ✅ 204 No Content | ☐ |
| 2 | 打开 Grafana Explore | ✅ 显示查询界面 | ☐ |
| 3 | 输入查询 {job="soc-copilot"} | ✅ 查询框有内容 | ☐ |
| 4 | 点击 Run query | ✅ 显示 4 条日志 | ☐ |
| 5 | 查看日志详情 | ✅ JSON 内容正确 | ☐ |
| 6 | 测试标签过滤 | ✅ 过滤工作正常 | ☐ |

---

## 🎉 成功标准

### 完全成功的标志

- ✅ 发送脚本返回 204 状态码
- ✅ Grafana 显示 4 条日志流
- ✅ 每条日志都有正确的标签
- ✅ 日志内容是有效的 JSON
- ✅ 时间戳在正确范围内
- ✅ 可以展开查看完整内容
- ✅ 过滤功能正常工作

---

**准备好了？运行以下命令开始测试**:

```bash
./send_test_alert.sh
```

然后在 Grafana 中查看结果！
