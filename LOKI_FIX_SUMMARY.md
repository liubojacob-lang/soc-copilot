# ✅ Loki 404 问题已解决

## 问题原因

**Loki 没有独立的 Web UI 界面！**

- ❌ `http://localhost:3100/` → 404 (正常现象)
- ✅ Loki 是纯 API 服务，不是 Web 界面
- ✅ 需要通过 **Grafana** 查看日志

---

## ✅ 验证结果

### 1. Loki 服务状态

```bash
✅ Loki 容器运行正常
✅ 端口映射正确: 3100:3100
✅ API 端点工作正常
```

### 2. API 端点测试

| 端点 | 状态 | 说明 |
|------|------|------|
| `/ready` | ✅ 200 | 健康检查 |
| `/config` | ✅ 200 | 配置信息 |
| `/loki/api/v1/push` | ✅ 204 | 推送日志 |
| `/` | ❌ 404 | **正常！无 UI** |

### 3. 测试告警已发送

```bash
✅ 测试告警已成功推送到 Loki
✅ 可以通过 API 查询到告警
✅ 可以在 Grafana 中查看
```

---

## 🎯 正确使用方式

### 方式 1: 通过 Grafana（推荐）⭐⭐⭐⭐⭐

```
1. 访问: http://localhost:3001
2. 登录: admin / admin
3. Explore → 选择 Loki 数据源
4. 查询: {job="soc-copilot"}
5. Run query
```

### 方式 2: 通过 API

```bash
# 查询日志
curl -G "http://localhost:3100/loki/api/v1/query" \
  --data-urlencode 'query={job="soc-copilot"}' | jq '.'
```

---

## 📊 架构说明

```
┌──────────────┐
│  SOC Copilot │ → 发送告警
│   Backend    │
└──────┬───────┘
       │
       ↓ HTTP API
┌──────────────┐
│     Loki     │ → 存储日志 (3100)
└──────┬───────┘
       │
       ↓ 查询 API
┌──────────────┐
│   Grafana    │ → 可视化界面 (3001)
└──────────────┘
```

**关键点**：
- ✅ Loki 只负责存储和 API
- ✅ Grafana 提供可视化界面
- ✅ 不直接访问 Loki 查看日志

---

## 🚀 快速开始：查看已发送的告警

### 在 Grafana 中查看

1. **打开浏览器访问**
   ```
   http://localhost:3001
   ```

2. **登录**
   ```
   用户名: admin
   密码: admin
   ```

3. **添加 Loki 数据源**（如果还没添加）
   ```
   左侧菜单 → Configuration (⚙️) → Data sources
   → Add data source → 选择 "Loki"
   → URL: http://loki:3100
   → Save & Test
   ```

4. **查看告警**
   ```
   左侧菜单 → Explore (搜索图标)
   → 数据源选择: "Loki"
   → 查询框输入: {job="soc-copilot"}
   → 时间范围: "Last 5 minutes"
   → 点击 "Run query"
   ```

5. **应该能看到测试告警！**
   - 日志内容: "Test alert from SOC Copilot"
   - 标签: job="soc-copilot", level="info", event_type="system_test"

---

## 📝 常用 Loki API 端点

```bash
# 健康检查
curl http://localhost:3100/ready

# 查看配置
curl http://localhost:3100/config

# 推送日志
curl -X POST http://localhost:3100/loki/api/v1/push \
  -H 'Content-Type: application/json' \
  -d '{"streams":[{"stream":{"job":"test"},"values":[["'$(
date +%s)000000000'","test"]]}]}'

# 查询日志
curl -G "http://localhost:3100/loki/api/v1/query" \
  --data-urlencode 'query={job="soc-copilot"}'

# 标签查询
curl -G "http://localhost:3100/loki/api/v1/label" \
  --data-urlencode 'start='$(date -v-1H +%s)000000000
```

---

## 🎓 学习 LogQL（Loki 查询语言）

### 基本查询

```
# 所有日志
{job="soc-copilot"}

# 按标签过滤
{job="soc-copilot", level="critical"}

# 正则匹配
{job="soc-copilot"} =~ ".*ssh.*"

# 内容过滤
{job="soc-copilot"} |= "error"
{job="soc-copilot"} |~ "error.*fatal"
```

### 聚合查询

```
# 计数
count_over_time({job="soc-copilot"}[5m])

# 求和
sum_over_time({job="soc-copilot", level="critical"}[1h])

# 按类型分组
count by (event_type) ({job="soc-copilot"})
```

---

## ✅ 总结

| 问题 | 答案 |
|------|------|
| **Loki 显示 404？** | ✅ **正常现象**，Loki 没有 UI |
| **如何查看日志？** | ✅ 通过 **Grafana** (http://localhost:3001) |
| **Loki 是什么？** | ✅ 纯 **API 服务**，存储和查询日志 |
| **测试告警在哪？** | ✅ 已发送到 Loki，可在 Grafana 查看 |

---

## 🎯 下一步操作

### 立即行动（2分钟）

1. ✅ 打开 Grafana: http://localhost:3001
2. ✅ 登录: admin / admin
3. ✅ 配置 Loki 数据源（如果还没配置）
4. ✅ Explore → Loki → 查询: `{job="soc-copilot"}`
5. ✅ 看到测试告警！

### 后续操作

1. 导入 SOC Copilot 仪表板
2. 配置告警规则
3. 创建自定义面板
4. 测试更多功能

---

**记住**: 
- ❌ 不要直接访问 http://localhost:3100/
- ✅ 访问 http://localhost:3001 使用 Grafana 查看 Loki 日志

**文档参考**:
- `LOKI_USAGE_GUIDE.md` - 详细使用指南
- `COMPLETE_INTEGRATION_GUIDE.md` - 完整集成指南

---

**状态**: ✅ 问题已解决，服务正常工作
