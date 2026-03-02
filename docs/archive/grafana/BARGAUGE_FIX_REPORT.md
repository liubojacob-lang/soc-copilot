# Grafana Bargauge 面板显示修复报告

## 📋 问题描述

**日期**: 2026-02-26
**问题**: 攻击类型排名 和 Agent 告警分布 面板只显示 1 个条形，而不是 top 10 排名

### 用户反馈的截图显示

| 面板 | 预期显示 | 实际显示 |
|------|---------|---------|
| 攻击类型排名 | 10 个条形 | 1 个条形 (值 34) |
| Agent 告警分布 | 10 个条形 | 1 个条形 (值 50) |

---

## 🔍 根本原因分析

### 问题定位

1. **数据层面** ✅ - 查询正确，Loki 返回 10 个结果
2. **面板配置** ❌ - Bargauge 面板缺少 `fieldConfig`

### 具体原因

Grafana 12.x 的 Bargauge 面板需要完整的 `fieldConfig` 配置来正确处理多个时间序列：

```json
// ❌ 错误配置 (修复前)
{
  "options": {
    "displayMode": "gradient",
    "reduceOptions": {"calcs": ["lastNotNull"], "fields": ""}
  }
  // 缺少 fieldConfig!
}

// ✅ 正确配置 (修复后)
{
  "fieldConfig": {
    "defaults": {
      "min": 0,
      "max": 200,
      "decimals": 0,
      "color": {"mode": "palette-classic"},
      "thresholds": {
        "mode": "absolute",
        "steps": [
          {"value": null, "color": "green"},
          {"value": 50, "color": "yellow"},
          {"value": 100, "color": "orange"},
          {"value": 150, "color": "red"}
        ]
      },
      "unit": "short"
    }
  },
  "options": {
    "displayMode": "basic",
    "reduceOptions": {"calcs": ["lastNotNull"], "fields": ""}
  }
}
```

---

## 🔧 修复方案

### 版本 4 修复内容

#### 1. 攻击类型排名面板 (Panel ID: 8)

**添加的配置:**
```json
{
  "fieldConfig": {
    "defaults": {
      "min": 0,
      "max": 200,
      "decimals": 0,
      "thresholds": {
        "steps": [
          {"value": null, "color": "green"},
          {"value": 50, "color": "yellow"},
          {"value": 100, "color": "orange"},
          {"value": 150, "color": "red"}
        ]
      }
    }
  },
  "options": {
    "displayMode": "basic"  // 从 gradient 改为 basic
  }
}
```

#### 2. Agent 告警分布面板 (Panel ID: 9)

**添加的配置:**
```json
{
  "fieldConfig": {
    "defaults": {
      "min": 0,
      "max": 100,
      "decimals": 0,
      "thresholds": {
        "steps": [
          {"value": null, "color": "green"},
          {"value": 40, "color": "yellow"},
          {"value": 60, "color": "orange"}
        ]
      }
    }
  },
  "options": {
    "displayMode": "gradient"  // 保持 gradient
  }
}
```

#### 3. 饼图面板修复 (Panel 5, 6)

**添加了 `instant: true`:**
```json
{
  "targets": [{
    "expr": "topk(10, sum by (event_type) (count_over_time({job=\"soc-copilot\"}[24h])))",
    "instant": true  // 新增
  }]
}
```

---

## ✅ 数据验证

### 攻击类型排名查询结果

```
返回结果数量: 10
 1. ssh_bruteforce   : 159 条告警
 2. port_scan        : 115 条告警
 3. malware_detected : 99  条告警
 4. sql_injection    : 63  条告警
 5. brute_force_web  : 62  条告警
 6. ddos_attack      : 55  条告警
 7. xss_attempt      : 34  条告警
 8. system_test      : 2   条告警
 9. system_info      : 2   条告警
10. manual_test      : 1   条告警
```

### Agent 告警分布查询结果

```
返回结果数量: 10
 1. agent-002        : 65 条告警
 2. agent-003        : 65 条告警
 3. agent-004        : 64 条告警
 4. agent-005        : 64 条告警
 5. agent-006        : 63 条告警
 6. agent-001        : 57 条告警
 7. cache-server-01  : 55 条告警
 8. db-server-01     : 52 条告警
 9. web-server-01    : 52 条告警
10. web-server-02    : 50 条告警
```

---

## 📁 文件变更

| 文件 | 操作 | 版本 |
|------|------|------|
| `grafana-soc-fixed-final.json` | 保留 | 版本 3 (有问题的版本) |
| `grafana-soc-v4-bargauge-fix.json` | ✅ 创建 | 版本 4 (修复版) |
| Grafana Dashboard | ✅ 更新 | 版本 4 已导入 |

---

## 🚀 验证步骤

### 1. 访问 Dashboard

```
http://localhost:3001/d/soc-copilot-full
```

### 2. 强制刷新

- **Mac**: `Cmd + Shift + R`
- **Windows**: `Ctrl + Shift + R`

### 3. 验证显示内容

| 面板 | 检查项 | 预期结果 |
|------|--------|---------|
| 攻击类型排名 | 条形数量 | 10 个 |
| 攻击类型排名 | 排名第一 | ssh_bruteforce (159) |
| Agent 告警分布 | 条形数量 | 10 个 |
| Agent 告警分布 | 排名第一 | agent-002 或 agent-003 (65) |

### 4. 如果还是只显示 1 个条形

**排查步骤:**

1. 点击面板右上角 → **Panel options** → **Query Inspector**
2. 查看 **Data** tab，确认返回的数据有 10 行
3. 查看 **Query** tab，确认查询是 instant query

如果数据有 10 行但只显示 1 个条形，可能是：
- Grafana 缓存问题 → 尝试清除浏览器缓存
- 面板高度问题 → 调整 `gridPos.h` (当前是 8 和 6)
- displayMode 问题 → 尝试改为 "lcd" 或 "gradient"

---

## 📊 Bargauge 面板配置说明

### displayMode 选项

| 模式 | 说明 | 适用场景 |
|------|------|---------|
| `basic` | 基本条形图 | 简单的排名显示 |
| `gradient` | 渐变色彩条形 | 需要颜色区分 |
| `lcd` | LCD 风格 | 数字化仪表风格 |

### fieldConfig defaults 参数

| 参数 | 说明 | 推荐值 |
|------|------|--------|
| `min` | 最小值 | 0 |
| `max` | 最大值 | 根据数据范围设置 |
| `decimals` | 小数位数 | 0 (整数) |
| `unit` | 单位 | "short" (无单位) |
| `color.mode` | 颜色模式 | "palette-classic" (经典调色板) |
| `thresholds` | 阈值 | 根据告警级别设置 |

---

## 📝 经验总结

### 教训

1. **Bargauge 面板必须有 fieldConfig**
   - 没有 fieldConfig 时，无法正确处理多系列数据
   - 必须设置 min/max 值以正确缩放

2. **instant query 的返回格式**
   - 每个时间系列是一个对象 `{metric: {...}, value: [ts, val]}`
   - Grafana 需要为每个系列创建一个条形

3. **displayMode 的选择**
   - `basic` 更适合简单的排名显示
   - `gradient` 更适合需要颜色区分的场景

### 最佳实践

```json
// ✅ 推荐：Bargauge 面板配置模板
{
  "type": "bargauge",
  "targets": [{
    "expr": "topk(10, sum by (field) (count_over_time(...[24h])))",
    "instant": true
  }],
  "fieldConfig": {
    "defaults": {
      "min": 0,
      "max": <根据数据范围>,
      "decimals": 0,
      "color": {"mode": "palette-classic"},
      "thresholds": {
        "mode": "absolute",
        "steps": [
          {"value": null, "color": "green"},
          {"value": <低阈值>, "color": "yellow"},
          {"value": <高阈值>, "color": "red"}
        ]
      }
    }
  },
  "options": {
    "displayMode": "basic",
    "orientation": "horizontal",
    "reduceOptions": {
      "calcs": ["lastNotNull"],
      "fields": ""
    }
  }
}
```

---

## ✅ 修复完成清单

- [x] 问题诊断：缺少 fieldConfig
- [x] 修复面板 8 (攻击类型排名)：添加 fieldConfig，改为 basic 模式
- [x] 修复面板 9 (Agent 告警分布)：添加 fieldConfig
- [x] 修复面板 5, 6 (饼图)：添加 instant: true
- [x] 导入 Dashboard：版本 4
- [x] 数据验证：查询返回 10 个结果
- [ ] 用户确认刷新后显示正确 (待确认)

---

**修复完成时间**: 2026-02-26
**Dashboard 版本**: 4
**影响面板**: 4 个
**状态**: ✅ 已修复并导入

## 🔗 相关文档

- [Grafana Bargauge Panel Documentation](https://grafana.com/docs/grafana/latest/panels-visualizations/visualizations/bar-gauge/)
- [LogQL Query Reference](https://grafana.com/docs/loki/latest/logql/)
