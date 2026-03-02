# Grafana 查看测试告警 - 完整可视化指南

## 🎯 已发送的 4 条告警

### ✅ 告警清单

| # | 严重级别 | 事件类型 | 代理 ID | 源 IP |
|---|---------|---------|---------|--------|
| 1 | 🔴 Critical | malware_detected | agent-001 | 192.168.1.100 |
| 2 | 🟠 High | ssh_bruteforce | agent-002 | 10.0.0.5 |
| 3 | 🟡 Medium | port_scan | agent-003 | 172.16.0.50 |
| 4 | 🔵 Info | system_info | system | 127.0.0.1 |

---

## 📊 Grafana 中的预期结果

### 第 1 步: 打开 Explore 页面

**URL**: http://localhost:3001/explore

**预期界面**:
```
┌─────────────────────────────────────────────┐
│  Grafana                   [Last 5 minutes ▼] │
│                                              │
│  Explore                                      │
│                                              │
│  Query                                       │
│  ┌────────────────────────────────────────┐ │
│  │ Data source: [Select data source ▼]   │ │
│  │ Query:                                 │ │
│  │         [Enter query here]             │ │
│  │         [Run query]                    │ │
│  │                                        │ │
│  │ Labels:                                │ │
│  │                                        │ │
│  └────────────────────────────────────────┘ │
└─────────────────────────────────────────────┘
```

---

### 第 2 步: 选择 Loki 数据源并输入查询

**操作**:
1. 点击 "Data source" 下拉框 → 选择 **"Loki"**
2. 在查询框中输入: `{job="soc-copilot"}`

**预期界面**:
```
┌─────────────────────────────────────────────┐
│  Query: Loki                               │
│         {job="soc-copilot"}                 │
│         [Run query]                         │
│                                             │
│  Labels:                                    │
│  ┌─────────────────────────────────────┐   │
│  │ event_type  ▼                      │   │
│  │ agent_id    ▼                      │   │
│  │ level       ▼                      │   │
│  └─────────────────────────────────────┘   │
└─────────────────────────────────────────────┘
```

---

### 第 3 步: 点击 Run query - 预期结果

**预期界面 (完整显示)**:

```
┌────────────────────────────────────────────────────────────────────┐
│ Results: 4 streams                                              │
│                                                                 │
│ ┌─────────────────────────────────────────────────────────────┐  │
│ │ 🔴 Stream 1: malware_detected (critical)                   │  │
│ │    Timestamp: 2026-02-26 11:30:45                         │  │
│ │    Labels:                                                  │  │
│ │      job: soc-copilot                                       │  │
│ │      level: critical                                        │  │
│ │      event_type: malware_detected                           │  │
│ │      agent_id: agent-001                                    │  │
│ │      source_ip: 192.168.1.100                              │  │
│ │    ▼ Expand to see log content                              │  │
│ │    {"message": "Malware detected on host",                 │  │
│ │     "file": "trojan.exe",                                  │  │
│ │     "action": "quarantined"}                              │  │
│ └─────────────────────────────────────────────────────────────┘  │
│                                                                 │
│ ┌─────────────────────────────────────────────────────────────┐  │
│ │ 🟠 Stream 2: ssh_bruteforce (high)                          │  │
│ │    Timestamp: 2026-02-26 11:30:46                         │  │
│ │    Labels:                                                  │  │
│ │      job: soc-copilot                                       │  │
│ │      level: high                                            │  │
│ │      event_type: ssh_bruteforce                             │  │
│ │      agent_id: agent-002                                    │  │
│ │      source_ip: 10.0.0.5                                   │  │
│ │    ▼ Expand                                                │  │
│ │    {"message": "SSH brute force attack detected",          │  │
│ │     "attempts": 100,                                       │  │
│ │     "username": "root"}                                    │  │
│ └─────────────────────────────────────────────────────────────┘  │
│                                                                 │
│ ┌─────────────────────────────────────────────────────────────┐  │
│ │ 🟡 Stream 3: port_scan (medium)                             │  │
│ │    Timestamp: 2026-02-26 11:30:47                         │  │
│ │    Labels:                                                  │  │
│ │      level: medium                                          │  │
│ │      event_type: port_scan                                  │  │
│ │      agent_id: agent-003                                    │  │
│ │      source_ip: 172.16.0.50                                 │  │
│ │    {"message": "Port scan detected",                        │  │
│ │     "scanned_ports": [22, 80, 443, 3306],                  │  │
│ │     "duration": "5s"}                                      │  │
│ └─────────────────────────────────────────────────────────────┘  │
│                                                                 │
│ ┌─────────────────────────────────────────────────────────────┐  │
│ │ 🔵 Stream 4: system_info (info)                             │  │
│ │    Timestamp: 2026-02-26 11:30:48                         │  │
│ │    Labels:                                                  │  │
│ │      level: info                                            │  │
│ │      event_type: system_info                                │  │
│ │      agent_id: system                                       │  │
│ │      source_ip: 127.0.0.1                                   │  │
│ │    {"message": "System health check completed",             │  │
│ │     "status": "healthy",                                   │  │
│ │     "uptime": 3600}                                        │  │
│ └─────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────┘
```

---

## 🎨 不同视图模式

### 1. Logs 视图 (默认)

**特点**:
- ✅ 显示完整日志内容
- ✅ 标签颜色编码
- ✅ 可展开/折叠

**显示格式**:
```
🔴 2026-02-26 11:30:45 │ critical │ malware_detected │ 192.168.1.100
🟠 2026-02-26 11:30:46 │ high     │ ssh_bruteforce  │ 10.0.0.5
🟡 2026-02-26 11:30:47 │ medium   │ port_scan        │ 172.16.0.50
🔵 2026-02-26 11:30:48 │ info     │ system_info      │ 127.0.0.1
```

---

### 2. Table 视图

**切换方式**: 点击视图切换按钮 → 选择 **"Table"**

**预期表格**:

| Timestamp | Level | Event Type | Agent ID | Source IP | Message |
|-----------|-------|------------|----------|-----------|---------|
| 11:30:45 | critical | malware_detected | agent-001 | 192.168.1.100 | Malware detected on host |
| 11:30:46 | high | ssh_bruteforce | agent-002 | 10.0.0.5 | SSH brute force attack |
| 11:30:47 | medium | port_scan | agent-003 | 172.16.0.50 | Port scan detected |
| 11:30:48 | info | system_info | system | 127.0.0.1 | System health check |

---

## 🏷️ 标签详情

### 标签过滤器

在 Grafana 中，您会看到标签过滤器：

```
┌────────────────────────────────┐
│ event_type  ▼                 │
│ ┌────────────────────────────┐│
│ │ malware_detected (1)        ││
│ │ ssh_bruteforce (1)          ││
│ │ port_scan (1)               ││
│ │ system_info (1)             ││
│ └────────────────────────────┘│
│                                │
│ agent_id  ▼                   │
│ ┌────────────────────────────┐│
│ │ agent-001 (1)               ││
│ │ agent-002 (1)               ││
│ │ agent-003 (1)               ││
│ │ system (1)                  ││
│ └────────────────────────────┘│
│                                │
│ level  ▼                       │
│ ┌────────────────────────────┐│
│ │ critical (1)  ← 1条         ││
│ │ high (1)      ← 1条         ││
│ │ medium (1)    ← 1条         ││
│ │ info (1)      ← 1条         ││
│ └────────────────────────────┘│
└────────────────────────────────┘
```

**交互**: 点击标签值可以过滤，只显示该值的日志

---

## 📊 统计信息

### 查询统计面板

在查询结果下方，Grafana 会显示：

```
Stats
┌──────────────────────────────────────┐
│ Total streams:      4                 │
│ Total entries:      4                 │
│ Execution time:    < 50ms            │
│ Data scanned:      < 1KB             │
│ Splits:            2                 │
│ Shards:            2                 │
└──────────────────────────────────────┘
```

---

## 🎯 关键验证点

### ✅ 成功的标志

1. ✅ **"Results: 4 streams"** 显示在页面顶部
2. ✅ **4 个可展开的日志流** 显示在结果区域
3. ✅ **颜色编码**: 🔴 Critical / 🟠 High / 🟡 Medium / 🔵 Info
4. ✅ **标签可见**: job, level, event_type 等
5. ✅ **JSON 内容**: 可以展开查看完整 JSON
6. ✅ **时间戳**: 在最近 5 分钟内
7. ✅ **响应快速**: 查询时间 < 100ms

### ❌ 失败的标志（不应该看到）

- ❌ "No data found"
- ❌ "Query returned no results"
- ❌ 空白的结果区域
- ❌ 错误提示消息
- ❌ 超过 10 秒的加载时间

---

## 🔍 点击日志条目的预期内容

### 点击 Stream 1 (malware_detected)

展开后应该看到：

```
┌─────────────────────────────────────────────┐
│ Labels                                     │
│ ┌─────────────────────────────────────┐   │
│ │ job: soc-copilot                   │   │
│ │ level: critical                    │   │
│ │ event_type: malware_detected        │   │
│ │ agent_id: agent-001                │   │
│ │ source_ip: 192.168.1.100           │   │
│ │ service_name: soc-copilot           │   │
│ │ detected_level: critical            │   │
│ └─────────────────────────────────────┘   │
│                                             │
│ Full log                                    │
│ {                                          │
│   "message": "Malware detected on host",    │
│   "file": "trojan.exe",                    │
│   "action": "quarantined"                  │
│ }                                          │
│                                             │
│ Metadata                                    │
│ Line #1 of 1                               │
└─────────────────────────────────────────────┘
```

---

## 🎨 颜色编码说明

### 严重级别颜色

| 级别 | 颜色 | 示例 | 含义 |
|------|------|------|------|
| **critical** | 🔴 红色 | malware_detected | 立即响应 |
| **high** | 🟠 橙色 | ssh_bruteforce | 尽快处理 |
| **medium** | 🟡 黄色 | port_scan | 需要关注 |
| **info** | 🔵 蓝色 | system_info | 信息记录 |

---

## 📋 快速检查清单

### 在 Grafana 中确认以下内容：

- [ ] Explore 页面已打开
- [ ] Loki 数据源已选择
- [ ] 查询框显示: `{job="soc-copilot"}`
- [ ] Run query 按钮已点击
- [ ] 显示 "Results: 4 streams"
- [ ] 可以看到 4 条不同颜色的日志
- [ ] 点击日志可以展开查看内容
- [ ] 标签过滤器可以看到所有标签值
- [ ] 时间范围显示为 "Last 5 minutes"

---

## 🎉 完美成功的表现

### 当一切正常时，您会看到：

1. ⚡ **快速响应**: < 1 秒显示结果
2. 🎨 **清晰展示**: 4 条不同颜色的日志
3. 📊 **完整信息**: 标签、时间戳、内容齐全
4. 🔍 **可交互**: 可展开、过滤、搜索
5. 🎯 **准确数据**: 与发送的测试告警完全一致

---

## 📱 实际操作演示

### 5 秒快速操作

```
第 1 秒: 点击 Explore 图标
第 2 秒: 选择 Loki 数据源
第 3 秒: 输入查询 {job="soc-copilot"}
第 4 秒: 点击 Run query
第 5 秒: 看到 4 条日志！✅
```

---

## 🆘 故障排除

### 如果 Grafana 显示 "No data"

**可能原因 1**: 时间范围不对

**解决**: 
- 点击右上角时间选择器
- 选择 "Last 5 minutes"
- 或 "Last 15 minutes"

**可能原因 2**: 查询语法错误

**解决**:
- 确保输入: `{job="soc-copilot"}`
- 大括号必须存在
- 引号必须是双引号

**可能原因 3**: 数据源配置错误

**解决**:
- Configuration → Data sources → Loki
- 检查 URL 是 `http://loki:3100`
- 点击 "Test" 按钮

---

## 📊 预期结果总结

### 数字化验证

| 检查项 | 预期值 | 实际验证方法 |
|--------|--------|-------------|
| 返回流数 | 4 | 查看 "Results" 显示 |
| 日志条数 | 4 | 计数展开的流 |
| Critical 级别 | 1 | 红色日志数量 |
| High 级别 | 1 | 橙色日志数量 |
| Medium 级别 | 1 | 黄色日志数量 |
| Info 级别 | 1 | 蓝色日志数量 |
| 查询时间 | < 1s | 页面底部统计 |
| 时间范围 | 最近 5 分钟 | 时间戳显示 |

---

**现在您已经知道预期结果了！**

请在浏览器中打开: **http://localhost:3001/explore**

开始验证这些结果！🚀
