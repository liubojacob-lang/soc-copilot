#!/bin/bash
# MD 文档清理脚本
# 生成日期: 2026-03-02
# 用途: 清理项目根目录的过时 MD 文档

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 项目根目录
PROJECT_ROOT="/Users/levent/Desktop/sec"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  MD 文档清理脚本${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "⚠️  此脚本将执行以下操作："
echo "  1. 创建归档目录"
echo "  2. 删除过时的临时文档（8个）"
echo "  3. 移动报告到 docs/reports/"
echo "  4. 移动归档文档到 docs/archive/"
echo ""
echo -e "${YELLOW}建议：先备份当前目录${NC}"
echo ""

# 询问用户是否继续
read -p "是否继续？(yes/no): " confirm
if [ "$confirm" != "yes" ]; then
    echo "操作已取消"
    exit 0
fi

cd "$PROJECT_ROOT"

# Step 1: 创建目录结构
echo -e "${GREEN}[1/5] 创建目录结构...${NC}"
mkdir -p docs/archive/{grafana,wazuh,i18n,phases}
mkdir -p docs/reports
echo "  ✅ 目录创建完成"
echo ""

# Step 2: 删除明确过时的文档
echo -e "${GREEN}[2/5] 删除过时的临时文档...${NC}"
echo "  删除以下文档："
echo "    - NEXT_STEPS.md"
echo "    - QUICK_FIX_SUMMARY.md"
echo "    - QUICK_IMPORT_GUIDE.md"
echo "    - IMPORT_DASHBOARD_GUIDE.md"
echo "    - LOKI_FIX_SUMMARY.md"
echo "    - LOKI_USAGE_GUIDE.md"
echo "    - INTEGRATION_SUCCESS.md"
echo "    - COMPLETE_INTEGRATION_GUIDE.md"

rm -f NEXT_STEPS.md \
      QUICK_FIX_SUMMARY.md \
      QUICK_IMPORT_GUIDE.md \
      IMPORT_DASHBOARD_GUIDE.md \
      LOKI_FIX_SUMMARY.md \
      LOKI_USAGE_GUIDE.md \
      INTEGRATION_SUCCESS.md \
      COMPLETE_INTEGRATION_GUIDE.md

echo "  ✅ 删除完成（8个文件）"
echo ""

# Step 3: 移动报告到 docs/reports/
echo -e "${GREEN}[3/5] 移动报告到 docs/reports/...${NC}"
mv BACKEND_VERIFICATION_REPORT.md docs/reports/ 2>/dev/null || true
mv FRONTEND_VERIFICATION_REPORT.md docs/reports/ 2>/dev/null || true
mv VERIFICATION_COMPLETE.md docs/reports/ 2>/dev/null || true
mv COMPREHENSIVE_OPTIMIZATION_REPORT.md docs/reports/ 2>/dev/null || true
mv SYSTEM_OPTIMIZATION_RECOMMENDATIONS.md docs/reports/ 2>/dev/null || true
mv CODE_AUDIT_REPORT.md docs/reports/ 2>/dev/null || true
mv TEST_ALERT_RESULTS.md docs/reports/ 2>/dev/null || true
echo "  ✅ 移动完成"
echo ""

# Step 4: 移动归档文档
echo -e "${GREEN}[4/5] 移动归档文档到 docs/archive/...${NC}"

# Grafana 相关
mv GRAFANA_*.md docs/archive/grafana/ 2>/dev/null || true
mv DASHBOARD_*.md docs/archive/grafana/ 2>/dev/null || true
mv BARGAUGE_*.md docs/archive/grafana/ 2>/dev/null || true

# Wazuh 相关（保留迁移完成文档）
mv WAZUH_ALTERNATIVES.md docs/archive/wazuh/ 2>/dev/null || true
mv WAZUH_CLEANUP_*.md docs/archive/wazuh/ 2>/dev/null || true
mv WAZUH_STREAM_*.md docs/archive/wazuh/ 2>/dev/null || true

# I18N 相关
mv I18N_*.md docs/archive/i18n/ 2>/dev/null || true
mv TRANSLATION_KEYS_*.md docs/archive/i18n/ 2>/dev/null || true
mv 导航栏翻译*.md docs/archive/i18n/ 2>/dev/null || true
mv SAAS_I18N_*.md docs/archive/i18n/ 2>/dev/null || true

# 阶段报告
mv P*_COMPLETE_*.md docs/archive/phases/ 2>/dev/null || true
mv P*_UI_*.md docs/archive/phases/ 2>/dev/null || true

# 其他归档文档
mv AI_MODEL_LOADING_FIX.md docs/archive/ 2>/dev/null || true
mv DIFY_REMOVAL_COMPLETE.md docs/archive/ 2>/dev/null || true
mv PLAYBOOK_DEFINITIONS_FIX.md docs/archive/ 2>/dev/null || true
mv VIRTUAL_SCROLL_*.md docs/archive/ 2>/dev/null || true
mv GZIP_REMOVAL_COMPLETE.md docs/archive/ 2>/dev/null || true
mv NAVIGATION_*.md docs/archive/ 2>/dev/null || true

echo "  ✅ 移动完成"
echo ""

# Step 5: 显示结果
echo -e "${GREEN}[5/5] 清理结果统计...${NC}"

# 统计根目录剩余的 MD 文件
remaining=$(find . -maxdepth 1 -name "*.md" -type f | wc -l | tr -d ' ')

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  清理完成！${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "根目录剩余 MD 文档: $remaining 个"
echo ""
echo "保留的核心文档："
ls -1 *.md 2>/dev/null | grep -E "^(README|PROJECT_SUMMARY|ALERT_NOTES_FIX|TIME_SERIES_AGGREGATION_FIX|TEST_RISK_SCORE|COMPREHENSIVE_OPTIMIZATION_GUIDE)" || echo "  (已在 docs/ 中)"
echo ""
echo "归档位置："
echo "  docs/archive/grafana/  - Grafana 集成文档"
echo "  docs/archive/wazuh/    - Wazuh 清理文档"
echo "  docs/archive/i18n/     - 国际化文档"
echo "  docs/archive/phases/   - 阶段完成报告"
echo "  docs/reports/          - 验证和测试报告"
echo ""
echo -e "${YELLOW}建议：${NC}"
echo "  1. 检查归档目录确保无误"
echo "  2. 提交 git 更新（如果适用）"
echo "  3. 更新 README.md 中的文档链接"
echo ""
