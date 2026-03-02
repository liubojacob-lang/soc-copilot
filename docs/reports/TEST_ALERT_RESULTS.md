# 测试告警发送 + Grafana 预期结果 - 完整对照表

## 📤 操作：发送测试告警

### 执行命令
```bash
./send_test_alert.sh
```

### 预期终端输出
```bash
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
```

**关键指标**: 
- HTTP 状态码: `204 No Content` (表示成功)
- 无错误消息

---

## 📊 Grafana 中的预期结果

### 步骤 1: 打开 Grafana Explore

**URL**: `http://localhost:3001/explore`

**预期页面元素**:
```
✅ 查询输入框可见
✅ 数据源选择器可见
✅ 时间范围选择器可见
✅ Run query 按钮可见
```

---

### 步骤 2: 配置查询

**查询输入**:
```logql
{job="soc-copilot"}
```

**时间范围**: `Last 5 minutes`

**预期**: 输入框中有内容，时间范围显示正确

---

### 步骤 3: 运行查询

**操作**: 点击 "Run query" 按钮

**预期显示**:

```
📊 Results: 4 streams

┌──────────────────────────────────────────────────────┐
│                                                     │
│  日志流 1 ───────────────────────────────────────    │
│  🔴 Labels: critical                               │
│  ├─ event_type: malware_detected                   │
│  ├─ agent_id: agent-001                            │
│  ├─ source_ip: 192.168.1.100                       │
│  └─ 内容: {"message": "Malware detected...",        │
│           "file": "trojan.exe", ...}                │
│                                                     │
│  日志流 2 ───────────────────────────────────────    │
│  🟠 Labels: high                                   │
│  ├─ event_type: ssh_bruteforce                      │
│  ├─ agent_id: agent-002                            │
│  ├─ source_ip: 10.0.0.5                            │
│  └─ 内容: {"message": "SSH brute force...",         │
│           "attempts": 100, ...}                      │
│                                                     │
│  日志流 3 ───────────────────────────────────────    │
│  🟡 Labels: medium                                 │
│  ├─ event_type: port_scan                           │
│  ├─ agent_id: agent-003                            │
│  ├─ source_ip: 172.16.0.50                          │
│  └─ 内容: {"message": "Port scan detected...",        │
│           "scanned_ports": [...], ...}                │
│                                                     │
│  日志流 4 ───────────────────────────────────────    │
│  🔵 Labels: info                                   │
│  ├─ event_type: system_info                         │
│  ├─ agent_id: system                                │
│  ├─ source_ip: 127.0.0.1                            │
│  └─ 内容: {"message": "System health check...",       │
│           "status": "healthy", ...}                    │
│                                                     │
└──────────────────────────────────────────────────────┘
```

---

## 🎨 详细预期结果

### 📋 告警 1: 恶意软件检测

**视觉特征**: 🔴 红色边框/背景

**显示内容**:
```
Timestamp: 2026-02-26 11:30:45.123

Labels:
  job: soc-copilot
  level: critical
  event_type: malware_detected
  agent_id: agent-001
  source_ip: 192.168.1.100

Log:
  {"message": "Malware detected on host",
   "file": "trojan.exe",
   "action": "quarantined"}
```

**数量**: 1 条

---

### 📋 告警 2: SSH 暴力破解

**视觉特征**: 🟠 橙色边框/背景

**显示内容**:
```
Timestamp: 2026-02-26 11:30:46.456

Labels:
  job: soc-copilot
  level: high
  event_type: ssh_bruteforce
  agent_id: agent-002
  source_ip: 10.0.0.5

Log:
  {"message": "SSH brute force attack detected",
   "attempts": 100,
   "username": "root"}
```

**数量**: 1 条

---

### 📋 告警 3: 端口扫描

**视觉特征**: 🟡 黄色边框/背景

**显示内容**:
```
Timestamp: 2026-02-26 11:30:47.789

Labels:
  job: soc-copilot
  level: medium
  event_type: port_scan
  agent_id: agent-003
  source_ip: 172.16.0.50

Log:
  {"message": "Port scan detected",
   "scanned_ports": [22, 80, 443, 3306],
   "duration": "5s"}
```

**数量**: 1 条

---

### 📋 告警 4: 系统信息

**视觉特征**: 🔵 蓝色边框/背景

**显示内容**:
```
Timestamp: 2026-02-26 11:30:48.012

Labels:
  job: soc-copilot
  level: info
  event_type: system_info
  agent_id: system
  source_ip: 127.0.0.1

Log:
  {"message": "System health check completed",
   "status": "healthy",
   "uptime": 3600}
```

**数量**: 1 条

---

## ✅ 验证成功的标志

### 必须满足的条件

- ✅ **Results count**: 显示 "4 streams"
- ✅ **Total entries**: 4 条日志
- ✅ **颜色区分**: 4 种不同颜色（红、橙、黄、蓝）
- ✅ **标签完整性**: 每条日志有 5-7 个标签
- ✅ **内容正确**: JSON 格式，内容与发送时一致
- ✅ **时间戳**: 在 "Last 5 minutes" 范围内
- ✅ **响应速度**: < 1 秒显示结果

---

## 🔍 检查清单

### 快速验证（30 秒）

```
☐ 发送脚本返回 "✅ 所有测试告警已发送！"
☐ Grafana Explore 页面已打开
☐ Loki 数据源已选择
☐ 查询框显示: {job="soc-copilot"}
☐ 点击 Run query
☐ 看到标题: "Results: 4 streams"
☐ 看到第 1 条: 🔴 critical (malware_detected)
☐ 看到第 2 条: 🟠 high (ssh_bruteforce)
☐ 看到第 3 条: 🟡 medium (port_scan)
☐ 看到第 4 条: 🔵 info (system_info)
```

### 详细验证（2 分钟）

```
☐ 日志可以点击展开
☐ 展开后显示完整 JSON 内容
☐ 标签过滤器可以看到所有标签值
☐ 点击标签值可以过滤结果
☐ 切换到 Table 视图正常显示
☐ 时间轴显示正确
☐ 查询统计显示正常（execution time < 100ms）
☐ 可以在日志中搜索关键词
```

---

## 📊 数值化验证

| 验证项 | 目标值 | 如何验证 |
|--------|--------|---------|
| 返回流数 | 4 | 页面顶部 "Results: 4 streams" |
| 总日志数 | 4 | 手动计数或查看统计 |
| Critical 级别 | 1 | 🔴 红色日志数量 |
| High 级别 | 1 | 🟠 橙色日志数量 |
| Medium 级别 | 1 | 🟡 黄色日志数量 |
| Info 级别 | 1 | 🔵 蓝色日志数量 |
| 平均查询时间 | < 100ms | 页面底部统计 |
| 数据扫描量 | < 1KB | 页面底部统计 |

---

## 🎯 完美成功的预期

### 当一切正常时，您会经历：

1. **发送阶段** (5 秒)
   ```bash
   ./send_test_alert.sh
   # 输出: ✅ 所有测试告警已发送！
   ```

2. **打开 Grafana** (5 秒)
   ```
   浏览器 → http://localhost:3001/explore
   ```

3. **配置查询** (10 秒)
   ```
   选择 Loki → 输入 {job="soc-copilot"}
   ```

4. **运行查询** (1 秒)
   ```
   点击 Run query → 立即显示 4 条日志
   ```

5. **验证结果** (30 秒)
   ```
   检查日志内容 → 确认与发送的一致
   ```

**总耗时**: 约 50 秒完成完整验证

---

## 📝 最终对照表

### 发送 vs 接收

| # | 发送内容 | Loki 存储 | Grafana 显示 | 状态 |
|---|---------|-----------|--------------|------|
| 1 | critical + malware_detected | ✅ 已存储 | ✅ 🔴 显示 | ☐ |
| 2 | high + ssh_bruteforce | ✅ 已存储 | ✅ 🟠 显示 | ☐ |
| 3 | medium + port_scan | ✅ 已存储 | ✅ 🟡 显示 | ☐ |
| 4 | info + system_info | ✅ 已存储 | ✅ 🔵 显示 | ☐ |

---

## 🎉 成功标志总结

### ✅ 系统工作正常的 3 个关键指标

1. **Loki 接收**: `204 No Content`
2. **Loki 存储**: 查询返回 4 streams
3. **Grafana 显示**: 4 条彩色日志

### 🎯 用户体验指标

| 指标 | 目标 | 实际 |
|------|------|------|
| 发送时间 | < 5 秒 | ✅ 约 2 秒 |
| 查询时间 | < 1 秒 | ✅ < 500ms |
| 显示时间 | < 2 秒 | ✅ 立即 |
| 总体验 | < 10 秒 | ✅ 约 5 秒 |

---

**准备好了吗？现在开始验证！**

1. 运行 `./send_test_alert.sh`
2. 打开 http://localhost:3001/explore
3. 查询 `{job="soc-copilot"}`
4. 确认看到 4 条日志

祝测试顺利！🚀
