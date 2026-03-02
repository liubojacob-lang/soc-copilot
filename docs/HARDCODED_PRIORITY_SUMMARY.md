# 硬编码字符串优先级分类摘要

## 📊 统计概览

- **总硬编码字符串**: ~287 个
- **需要翻译**: ~100 个
- **保持原样（技术术语）**: ~187 个

---

## 🎯 Priority P0: 导航组件（关键 - 25个文件）

**影响文件:**
```
components/NavigationEnhanced.tsx
components/NavigationGrouped.tsx
components/GlobalSearch.tsx
components/common/MobileDrawer.tsx
```

**需要替换的字符串:**
| 原文 | 翻译键 | 中文 |
|------|--------|------|
| Triggers | navigation.triggers | 触发器 |
| Settings | navigation.settings | 设置 |
| Approvals | playbooks.tabs.approvals | 审批 |
| Definitions | navigation.definitions | 定义 |
| Playbooks | navigation.runs | 剧本运行 |
| AI Assistant | navigation.aiCopilot | AI 助手 |
| Alerts | navigation.alerts | 告警 |
| Assets | home.tabs.assets | 资产 |
| Reports | reports.title | 报告 |
| Threat Intel | navigation.threatIntel | 威胁情报 |
| Audit Logs | navigation.audit | 审计日志 |
| Timeline | tabs.timelineBuilder | 时间线 |

**执行命令:**
```bash
# 预览变更
python scripts/replace_hardcoded_strings.py --priority P0 --dry-run

# 应用变更
python scripts/replace_hardcoded_strings.py --priority P0
```

**预计时间**: 1-2 小时

---

## 🔥 Priority P1: 常用UI标签（高频 - 40+处）

**分类:**
- 状态标签: Unknown, Status
- 严重级别: Critical, High, Medium, Low
- 通用字段: Name, Type, Actions, Details

**需要替换的字符串:**
| 原文 | 翻译键 | 中文 |
|------|--------|------|
| Unknown | status.unknown | 未知 |
| Critical | severity.critical | 严重 |
| High | severity.high | 高 |
| Medium | severity.medium | 中 |
| Low | severity.low | 低 |
| Status | common.status | 状态 |
| Name | common.name | 名称 |
| Type | common.type | 类型 |
| Actions | common.actions | 操作 |
| Details | common.details | 详情 |

**影响文件**: ~40 个组件文件

**执行命令:**
```bash
python scripts/replace_hardcoded_strings.py --priority P1 --dry-run
python scripts/replace_hardcoded_strings.py --priority P1
```

**预计时间**: 2-3 小时

---

## 📈 Priority P2: 监控和仪表板标签（15+处）

**需要替换的字符串:**
| 原文 | 翻译键 | 中文 |
|------|--------|------|
| CPU | monitor.cpu | CPU |
| Memory | monitor.memory | 内存 |
| Latency | monitor.latency | 延迟 |
| Disk | monitor.disk | 磁盘 |
| Network | monitor.network | 网络 |

**影响文件**: ~15 个监控组件

**执行命令:**
```bash
python scripts/replace_hardcoded_strings.py --priority P2 --dry-run
python scripts/replace_hardcoded_strings.py --priority P2
```

**预计时间**: 1 小时

---

## 🔧 Priority P3: 技术术语（可选 - 保持原样）

**不需要翻译的技术术语:**
- HTTP 头: "Authorization", "Content-Type"
- API 路径: "/api/ai/chat", "/api/cloud-native/*"
- 技术常量: "GET", "POST", "PUT", "DELETE"
- 状态码: "200", "404", "500"

**处理**: 保持英文，不进行替换

---

## 📋 执行计划

### 第 1 周: P0 导航组件
- [ ] Day 1: 运行 `--priority P0 --dry-run` 预览
- [ ] Day 1: 审查 diff 输出
- [ ] Day 2: 应用 P0 变更
- [ ] Day 2: 测试所有导航组件
- [ ] Day 2: 测试中英文切换

### 第 2 周: P1 常用标签
- [ ] Day 1: 运行 `--priority P1 --dry-run` 预览
- [ ] Day 1-2: 审查并修复问题
- [ ] Day 3: 应用 P1 变更
- [ ] Day 4-5: 测试 UI 组件

### 第 3 周: P2 监控标签
- [ ] Day 1: 运行 `--priority P2 --dry-run`
- [ ] Day 1: 应用变更
- [ ] Day 2: 测试监控组件
- [ ] Day 3-5: 全面验证和修复

### 第 4 周: 验证和优化
- [ ] 运行 `python scripts/find_missing_translations.py`
- [ ] 运行 `python scripts/validate_i18n.py`
- [ ] 修复所有剩余问题
- [ ] 性能测试
- [ ] 文档更新

---

## 🛠️ 快速开始

### 1. 生成摘要（当前步骤）
```bash
python scripts/replace_hardcoded_strings.py --summary
```

### 2. 预览 P0 变更
```bash
python scripts/replace_hardcoded_strings.py --priority P0 --dry-run
```

### 3. 应用 P0 变更
```bash
python scripts/replace_hardcoded_strings.py --priority P0
```

### 4. 验证
```bash
python scripts/find_missing_translations.py
python scripts/validate_i18n.py
```

### 5. 回滚（如需要）
```bash
git checkout frontend/components/
```

---

## 📝 注意事项

1. **备份**: 应用变更前先提交当前代码
   ```bash
   git add .
   git commit -m "backup: before hardcoded string replacement"
   ```

2. **测试**: 每个优先级应用后都要测试
   - 功能测试
   - 语言切换测试
   - 视觉回归测试

3. **代码审查**: 检查生成的 diff 是否正确

4. **渐进式**: 按优先级逐步进行，不要一次性全部替换

---

## ✅ 成功标准

- [ ] 所有导航组件使用翻译
- [ ] 所有常用 UI 标签使用翻译
- [ ] 监控组件使用翻译
- [ ] 中英文切换正常工作
- [ ] 无 TypeScript 类型错误
- [ ] 所有测试通过
- [ ] 无硬编码字符串残留（技术术语除外）

---

**生成时间**: 2026-02-27 09:27:53
**状态**: 待执行
**文档**: HARDCODED_PRIORITY_SUMMARY.md
