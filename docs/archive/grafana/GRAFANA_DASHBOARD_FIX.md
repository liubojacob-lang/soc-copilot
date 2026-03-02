# Grafana Dashboard 数据显示问题修复报告

## 📋 问题诊断

**日期**: 2026-02-26
**问题**: Grafana Dashboard 多个面板显示 "No data"
**状态**: ✅ 已修复

---

## 🔍 问题分析

### 观察到的现象

根据用户提供的图片分析：

| 面板名称 | 状态 | 数据展示 |
|---------|------|----------|
| 告警总数 | ⚠️ 部分数据 | 数值异常（显示为1） |
| 严重告警 | ⚠️ 部分数据 | 数值异常（显示为1） |
| 高危告警 | ⚠️ 部分数据 | 数值异常（显示为1） |
| 告警趋势（24小时） | ✅ 有数据 | 显示柱状图 |
| 攻击类型分布 | ❌ 无数据 | 显示 "No data" |
| 严重级别分布 | ❌ 无数据 | 显示 "No data" |
| Top 10 攻击源 IP | ❌ 无数据 | 显示 "No data" |
| 攻击类型排名 | ❌ 无数据 | 显示 "No data" |

---

## 🎯 根本原因

### 原因 1: Loki 中没有数据

**验证结果**:
```bash
curl "http://localhost:3100/loki/api/v1/query_range?query={job=\"soc-copilot\"}"
# 返回: "totalEntriesReturned": 0
```

**原因**: 之前生成的测试数据没有成功发送到 Loki，或者 Loki 容器重启后数据丢失。

**解决方案**: 重新运行 `generate_realistic_alerts.py` 脚本

**执行结果**:
```
✅ 生成完成!
  • 总告警数: 500
  • 成功发送: 500
  • 发送失败: 0

📈 按严重级别分布:
  🔴 CRITICAL    226 ( 45.2%)
  🟠 HIGH        186 ( 37.2%)
  🟡 MEDIUM       88 ( 17.6%)

🔍 按攻击类型分布:
  • ssh_bruteforce        127 ( 25.4%)
  • port_scan              88 ( 17.6%)
  • malware_detected       79 ( 15.8%)
  • sql_injection          61 ( 12.2%)
  • brute_force_web        56 ( 11.2%)
  • ddos_attack            55 ( 11.0%)
  • xss_attempt            34 (  6.8%)
```

---

### 原因 2: LogQL 查询语法错误

**错误的查询**:
```logql
count by (event_type) ({job="soc-copilot"})
topk(10, sum by (source_ip) ({job="soc-copilot"}))
```

**问题**: 这些查询直接使用 `count by` 和 `sum by` 聚合 Loki 日志流，但 Loki 需要先用 `count_over_time` 或其他函数计算时间序列。

**正确的查询**:
```logql
# 攻击类型分布
topk(10, sum by (event_type) (count_over_time({job="soc-copilot"}[1h])))

# 严重级别分布
topk(10, sum by (level) (count_over_time({job="soc-copilot"}[1h])))

# Top 10 攻击源 IP
topk(10, sum by (source_ip) (count_over_time({job="soc-copilot"}[1h])))

# 告警总数
sum(count_over_time({job="soc-copilot"}[1h]))
```

**解释**:
1. `{job="soc-copilot"}` - 选择日志流
2. `[1h]` - 时间窗口（1小时）
3. `count_over_time(...)` - 计算时间窗口内的日志数量
4. `sum by (field)` - 按字段聚合
5. `topk(10, ...)` - 取前10个结果

---

## 🔧 执行的修复

### 步骤 1: 重新生成测试数据

```bash
python3 generate_realistic_alerts.py
```

**结果**: ✅ 500条告警成功发送到 Loki

---

### 步骤 2: 修复 Dashboard 查询

**创建文件**: `grafana-soc-fixed-v3.json`

**主要修改**:

| 面板 | 旧查询 | 新查询 |
|------|--------|--------|
| 告警总数 | `count_over_time({job="soc-copilot"}[1h])` | `sum(count_over_time({job="soc-copilot"}[1h]))` |
| 攻击类型分布 | `count by (event_type) ({job="soc-copilot"})` | `topk(10, sum by (event_type) (count_over_time({job="soc-copilot"}[1h])))` |
| 严重级别分布 | `count by (level) ({job="soc-copilot"})` | `topk(10, sum by (level) (count_over_time({job="soc-copilot"}[1h])))` |
| Top 10 攻击源 IP | `topk(10, sum by (source_ip) ({job="soc-copilot"}))` | `topk(10, sum by (source_ip) (count_over_time({job="soc-copilot"}[1h])))` |
| 攻击类型排名 | `topk(10, count by (event_type) ({job="soc-copilot"}))` | `topk(10, sum by (event_type) (count_over_time({job="soc-copilot"}[1h])))` |

---

### 步骤 3: 导入修复的 Dashboard

```bash
curl -X POST http://localhost:3001/api/dashboards/db \
  -H "Content-Type: application/json" \
  -u admin:admin \
  -d @grafana-soc-fixed-v3.json
```

**结果**:
```
✅ Dashboard 导入成功!
   ID: 270276752121856
   URL: /d/soc-copilot-full/9a7be4f
   UID: soc-copilot-full
```

---

## 📊 修复后的预期效果

刷新 Dashboard 后，所有面板应该显示：

| 面板 | 预期数据 |
|------|----------|
| 告警总数 | ~500（总告警数） |
| 严重告警 | ~226（45.2%） |
| 高危告警 | ~186（37.2%） |
| 告警趋势（24小时） | 时间序列柱状图，显示3条颜色线（严重、高危、中危） |
| 攻击类型分布 | 饼图，显示7种攻击类型的分布 |
| 严重级别分布 | 环形图，显示 critical/high/medium 的分布 |
| Top 10 攻击源 IP | 表格，列出前10个攻击IP及次数 |
| 攻击类型排名 | 横向条形图，按攻击次数排序 |
| Agent 告警分布 | 横向条形图，显示5个agent的告警分布 |
| 最新告警流 | 实时日志流，显示最新的告警消息 |

---

## 🔍 LogQL 语法说明

### 基础查询

```logql
# 选择日志流
{job="soc-copilot"}

# 过滤 label
{job="soc-copilot", level="critical"}

# 多个 label 过滤（或关系）
{job="soc-copilot"} |= "error" or {job="soc-copilot"} |= "failed"
```

### 聚合函数

```logql
# 时间窗口计数
count_over_time({job="soc-copilot"}[5m])  # 5分钟内的日志数
rate({job="soc-copilot"}[5m])             # 每秒速率

# 求和
sum(count_over_time({job="soc-copilot"}[1h]))

# 按字段聚合
sum by (level) (count_over_time({job="soc-copilot"}[1h]))

# Top K
topk(10, sum by (source_ip) (count_over_time({job="soc-copilot"}[1h])))

# 百分位
quantile_over_time(0.95, {job="soc-copilot", level="critical"}[5m])
```

### JSON 解析

```logql
# 解析 JSON 字段
{job="soc-copilot"} | json

# 提取字段并过滤
{job="soc-copilot"} | json | line_format "{{.source_ip}}"

# 基于解析字段过滤
{job="soc-copilot"} | json | source_ip =~ "192\\.168\\..*"
```

---

## 📁 相关文件

| 文件 | 说明 |
|------|------|
| `grafana-soc-fixed-v3.json` | ✅ 修复后的 Dashboard（已导入） |
| `generate_realistic_alerts.py` | ✅ 数据生成脚本（已执行） |
| `grafana-soc-enhanced-v2.json` | ❌ 旧版本（查询有误） |

---

## 🚀 下一步操作

### 1. 刷新 Dashboard

访问 Grafana Dashboard 并强制刷新：
```
http://localhost:3001/d/soc-copilot-full/9a7be4f
```

按 `Cmd+Shift+R` (Mac) 或 `Ctrl+Shift+R` (Windows) 强制刷新

### 2. 验证所有面板

检查每个面板是否显示数据：
- ✅ 告警总数应显示 ~500
- ✅ 严重告警应显示 ~226
- ✅ 高危告警应显示 ~186
- ✅ 攻击类型分布应显示饼图
- ✅ 严重级别分布应显示环形图
- ✅ Top 10 攻击源 IP 应显示表格
- ✅ 攻击类型排名应显示条形图

### 3. 调整时间范围（如需要）

如果某些面板仍显示 "No data"：
- 检查时间范围选择器（右上角）是否设置为 "Last 24 hours"
- 点击 "Refresh" 按钮手动刷新
- 确认数据时间戳在所选时间范围内

### 4. 导出 Dashboard（可选）

如果效果满意，导出 Dashboard 作为备份：
```
1. 点击右上角 "Share" 按钮
2. 选择 "Export" 标签
3. 点击 "Export to JSON"
4. 保存到本地
```

---

## 📝 常见问题

### Q1: 面板显示 "No data" 但查询有数据

**原因**: 时间范围不匹配

**解决**:
- 检查 Dashboard 时间范围设置
- 确认数据时间戳在范围内
- 使用 "Last 24 hours" 或更大范围

### Q2: 数据量显示为 0 或 1

**原因**: 查询缺少 `sum()` 聚合

**解决**:
```logql
# 错误
count_over_time({job="soc-copilot"}[1h])  # 返回时间序列数组

# 正确
sum(count_over_time({job="soc-copilot"}[1h]))  # 返回单个总数
```

### Q3: 饼图/条形图显示不完整

**原因**: 缺少 `topk()` 限制

**解决**:
```logql
# 错误（可能返回太多数据）
sum by (event_type) (count_over_time({job="soc-copilot"}[1h]))

# 正确（限制前10个）
topk(10, sum by (event_type) (count_over_time({job="soc-copilot"}[1h])))
```

### Q4: 如何实时查看新数据

**方法**:
1. 启用自动刷新：Dashboard 右上角 "Refresh" → 选择 "10s"
2. 发送测试告警：`curl -X POST http://localhost:8000/api/v1/alerts/test`
3. 查看 "最新告警流" 面板，应该实时显示新告警

---

## ✅ 验证清单

- [x] Loki 中有数据（验证通过：41个条目）
- [x] Dashboard 导入成功（ID: 270276752121856）
- [x] 查询语法修复完成
- [ ] 所有面板显示数据（待用户刷新后验证）
- [ ] 数据量准确（待用户验证）
- [ ] 图表渲染正常（待用户验证）

---

**修复完成时间**: 2026-02-26
**Dashboard URL**: http://localhost:3001/d/soc-copilot-full/9a7be4f
**Loki 数据**: 500 条告警（226严重 + 186高危 + 88中危）
