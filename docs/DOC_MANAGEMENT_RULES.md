# 文档管理规定

## 📁 文档存储规则

**所有文档必须统一放在 `docs/` 文件夹里**

---

## 📂 文件夹结构

```
docs/
├── week1/                          # Week 1 文档
│   ├── README_WEEK1.md            # Week 1 快速参考
│   ├── WAZUH_DEEP_INTEGRATION_PLAN.md  # 实施计划
│   ├── WEEK_1_COMPLETION_REPORT.md     # 完成报告
│   ├── WEEK_1_FINAL_REPORT.md          # 最终报告
│   ├── WEEK1_FINAL_HANDOVER.md         # 交接文档
│   ├── WEEK1_BROWSER_TEST_SUCCESS.md   # 测试成功报告
│   ├── guides/                    # 指南文档
│   │   ├── BROWSER_TEST_QUICK_REF.md
│   │   └── TEST_GUIDE_WEEK1.md
│   └── reports/                   # 报告文档
│       ├── PORT_3003_CONFIRMED.md
│       ├── PORT_3000_FINAL_REPORT.md
│       ├── PORT_CONFIGURATION.md
│       ├── PORT_UPDATE_COMPLETE.md
│       └── FINAL_TEST_REPORT_WEEK1.md
├── week2/                          # Week 2 文档 (待创建)
├── guides/                         # 通用指南
├── reports/                        # 通用报告
└── DOC_MANAGEMENT_RULES.md         # 本文件
```

---

## 📝 文档命名规则

### 通用规则

- 使用大写字母和下划线
- 例如: `WEEK_1_COMPLETION_REPORT.md`

### 特定类型

- **README**: `README_WEEK1.md`
- **计划**: `*_PLAN.md`
- **报告**: `*_REPORT.md`
- **指南**: `*_GUIDE.md`
- **测试**: `TEST_*.md`

---

## 📋 文档分类

### 按周分类

```
docs/week1/
docs/week2/
docs/week3/
...
```

### 按类型分类

```
guides/     - 指南和教程
reports/    - 测试和完成报告
plans/      - 实施计划
```

---

## ✅ 创建新文档时

1. **确定分类** - 属于哪一周/哪个项目
2. **选择位置** - 放入对应的 docs 子文件夹
3. **命名规范** - 遵循命名规则
4. **更新索引** - 在 README 中添加链接

---

## 🚫 禁止行为

- ❌ 不要在项目根目录创建文档
- ❌ 不要使用中文文件名
- ❌ 不要使用特殊字符 (除 \_ 和 -)
- ❌ 不要随意移动文档位置

---

## 📌 例外情况

**允许放在根目录的文件**:

- `README.md` - 项目主 README
- `.env.example` - 环境变量示例
- `package.json` - 依赖配置
- 其他配置文件

---

## 🔄 迁移现有文档

### 待迁移文档

以下根目录文档需要迁移到 `docs/`:

- [ ] BUILD_FIX_REPORT.md
- [ ] DIAGNOSTIC_REPORT.md
- [ ] HYDRATION_FIX_REPORT.md
- [ ] IMPLEMENTATION_REPORT.md
- [ ] P0_BUG_FIX_REPORT.md
- [ ] P0_IMPLEMENTATION_REPORT.md
- [ ] P1_PROGRESS_REPORT.md
- [ ] P1_TEST_REPORT.md
- [ ] README_AUDIT_REPORTS.md
- [ ] TEST_REPORT_NOTIFICATIONS.md
- [ ] TEST_REPORT.md
- [ ] 其他 \*.md 文档

---

## 📞 快速参考

### 创建新文档

```bash
# Week 文档
touch docs/week2/WEEK_2_PLAN.md

# 通用指南
touch docs/guides/SOMETHING_GUIDE.md

# 报告
touch docs/reports/SOMETHING_REPORT.md
```

### 查找文档

```bash
# 查找所有 Week 文档
ls docs/week*/

# 查找所有指南
ls docs/guides/

# 查找所有报告
ls docs/reports/
```

---

**规定生效日期**: 2026-02-25
**规定制定**: SOC Copilot Team

🎯 **记住: 所有文档统一放在 docs/ 文件夹！**
