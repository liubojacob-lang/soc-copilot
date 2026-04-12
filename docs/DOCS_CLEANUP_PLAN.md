# 文档清理计划

**日期**: 2026-02-25
**目的**: 清理重复、过时、无用的 markdown 文档

---

## 📋 清理清单

### 第一批：测试相关报告（删除）

这些是 P0/P1 阶段的临时报告，已有最终版本

- [ ] P0_BUG_FIX_REPORT.md
- [ ] P0_COMPLETE_SUMMARY.md
- [ ] P0_IMPLEMENTATION_REPORT.md
- [ ] P1_FINAL_SUMMARY.md
- [ ] P1_IMPLEMENTATION_COMPLETE.md
- [ ] P1_PHASE2_COMPLETE.md
- [ ] P1_PROGRESS_REPORT.md
- [ ] P1_TEST_REPORT.md
- [ ] TEST_REPORT.md
- [ ] TEST_SUMMARY.md
- [ ] TEST_REPORT_NOTIFICATIONS.md

### 第二批：Wazuh 临时报告（删除）

Week 1 有完整版本，这些临时版本可删除

- [ ] WAZUH_DEPLOYMENT.md
- [ ] WAZUH_DEPLOYMENT_SUCCESS.md
- [ ] WAZUH_FIXED.md
- [ ] WAZUH_IMPLEMENTATION_SUMMARY.md

### 第三批：过时的修复报告（删除）

问题已修复，无需保留

- [ ] BUILD_FIX_REPORT.md
- [ ] FRONTEND_STARTUP_FIX.md
- [ ] HYDRATION_FIX_REPORT.md
- [ ] HYDRATION_FIX_SUMMARY.md

### 第四批：临时状态报告（删除）

- [ ] BACKEND_RUNNING_STATUS.md
- [ ] STARTUP_STATUS.md
- [ ] DEPLOYMENT_STATUS.md

### 第五批：临时/草稿（删除）

- [ ] WEEK1_SIMPLE_WAZUH_PAGE.md
- [ ] NEXT_STEPS.md
- [ ] next_steps_plan.md

### 第六批：分析报告（移至 docs/archive/）

有价值但不是当前重点的文档

- [ ] BACKEND_FRONTEND_GAP_ANALYSIS.md → docs/archive/
- [ ] COMPREHENSIVE_API_AUDIT.md → docs/archive/
- [ ] DIAGNOSTIC_REPORT.md → docs/archive/
- [ ] IMPLEMENTATION_REPORT.md → docs/archive/
- [ ] INTEGRATION_COMPLETE.md → docs/archive/
- [ ] INTEGRATION_SUMMARY.md → docs/archive/
- [ ] MISSING_FRONTEND_FEATURES.md → docs/archive/
- [ ] OPTIMIZATION_RECOMMENDATIONS.md → docs/archive/
- [ ] TECHNICAL_ARCHITECTURE_ANALYSIS.md → docs/archive/

### 第七批：快速参考（整合到 docs/guides/）

- [ ] ALERTS_API_QUICK_REF.md → docs/guides/
- [ ] API_ENDPOINT_REFERENCE.md → docs/guides/
- [ ] FEISHU_QUICK_REF.md → docs/guides/
- [ ] FEISHU_QUICKSTART.md → docs/guides/

### 第八批：整合到 docs/（删除根目录版本）

内容已在 docs/ 中有更新版本

- [ ] ACCESS_GUIDE.md (已有 docs/00-getting-started.md)
- [ ] DEPLOY.md (已有 docs/09-ops-deploy.md)
- [ ] QUICKSTART_INTEGRATION.md (已有 docs/00-getting-started.md)
- [ ] QUICKSTART_NOTIFICATIONS.md (已有 docs/FEISHU_SETUP_GUIDE.md)
- [ ] README_AUDIT_REPORTS.md (内容已整合)
- [ ] SECURITY_INTEGRATION_PLAN.md (已有 docs/08-security.md)

### 第九批：保留在根目录

核心文档保留

- ✓ README.md (项目主文档)
- ✓ PROJECT_SUMMARY.md (项目总结)
- ✓ SOC*Copilot_v0.8*开发路线图\_20260224.md
- ✓ SOC*Copilot*统一技术文档.md
- ✓ 功能对比矩阵\_20260224.md
- ✓ 功能模块全面梳理报告.md

---

## 🗂️ 文件夹结构（清理后）

```
/
├── README.md                          # 项目主文档
├── PROJECT_SUMMARY.md                 # 项目总结
├── SOC_Copilot_v0.8_开发路线图_20260224.md
├── SOC_Copilot_统一技术文档.md
├── 功能对比矩阵_20260224.md
├── 功能模块全面梳理报告.md
├── docs/                              # 所有文档
│   ├── README.md
│   ├── week1/                         # Week 1 文档
│   ├── week2/                         # Week 2 文档
│   ├── archive/                       # 归档文档
│   ├── guides/                        # 指南
│   └── zh/                            # 中文文档
└── ...
```

---

## ✅ 预期结果

清理后根目录只保留：

- 6 个核心文档
- 所有其他文档在 docs/ 中
- 结构清晰，易于维护

**文档数量**: 从 60+ 个减少到 6 个核心文档
