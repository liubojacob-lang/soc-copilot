#!/bin/bash
# SOC Copilot - GitHub Labels 初始化脚本
# 创建代码审查相关的GitHub标签
# 关联需求：FR-002（代码审查流程管理）
#
# 使用方法：
#   gh auth login  # 先登录GitHub CLI
#   ./scripts/setup-review-labels.sh [repo-owner/repo-name]
#
# 如果不指定repo，则使用当前git remote的仓库

set -euo pipefail

REPO="${1:-}"

if [ -z "$REPO" ]; then
    REPO=$(gh repo view --json nameWithOwner -q '.nameWithOwner' 2>/dev/null || echo "")
fi

if [ -z "$REPO" ]; then
    echo "错误: 无法确定仓库。请运行: $0 owner/repo"
    exit 1
fi

echo "为仓库 $REPO 创建代码审查标签..."

# =============================================================================
# 审查意见分类标签
# =============================================================================
echo "创建审查意见分类标签..."

gh label create "review:must-fix" \
    --repo "$REPO" \
    --color "FF0000" \
    --description "必须修改 - 阻塞性问题，不修改不予合并" \
    --force || true

gh label create "review:suggest" \
    --repo "$REPO" \
    --color "FFAB00" \
    --description "建议修改 - 改进性建议，可采纳可不采纳" \
    --force || true

gh label create "review:comment" \
    --repo "$REPO" \
    --color "0E8A16" \
    --description "仅评论 - 知识分享或疑问，无需代码变更" \
    --force || true

# =============================================================================
# 变更类型标签
# =============================================================================
echo "创建变更类型标签..."

gh label create "type:feat" \
    --repo "$REPO" \
    --color "0075CA" \
    --description "功能新增" \
    --force || true

gh label create "type:fix" \
    --repo "$REPO" \
    --color "D73A4A" \
    --description "Bug修复" \
    --force || true

gh label create "type:refactor" \
    --repo "$REPO" \
    --color "C5DEF5" \
    --description "代码重构" \
    --force || true

gh label create "type:security" \
    --repo "$REPO" \
    --color "B60205" \
    --description "安全修复 ⚠️" \
    --force || true

gh label create "type:perf" \
    --repo "$REPO" \
    --color "1D76DB" \
    --description "性能优化" \
    --force || true

gh label create "type:docs" \
    --repo "$REPO" \
    --color "0075CA" \
    --description "文档更新" \
    --force || true

gh label create "type:test" \
    --repo "$REPO" \
    --color "C2E0C6" \
    --description "测试补充" \
    --force || true

gh label create "type:config" \
    --repo "$REPO" \
    --color "FBCA04" \
    --description "配置变更" \
    --force || true

gh label create "type:migration" \
    --repo "$REPO" \
    --color "E99695" \
    --description "数据库迁移" \
    --force || true

# =============================================================================
# 影响范围标签
# =============================================================================
echo "创建影响范围标签..."

gh label create "scope:backend" \
    --repo "$REPO" \
    --color "006B75" \
    --description "仅影响后端" \
    --force || true

gh label create "scope:frontend" \
    --repo "$REPO" \
    --color "E99695" \
    --description "仅影响前端" \
    --force || true

gh label create "scope:fullstack" \
    --repo "$REPO" \
    --color "BFDADC" \
    --description "前后端均有变更" \
    --force || true

gh label create "scope:infra" \
    --repo "$REPO" \
    --color "BFD4F2" \
    --description "基础设施(K8s/CI/CD)" \
    --force || true

gh label create "scope:security" \
    --repo "$REPO" \
    --color "B60205" \
    --description "安全相关 ⚠️" \
    --force || true

gh label create "scope:database" \
    --repo "$REPO" \
    --color "E99695" \
    --description "数据库变更" \
    --force || true

# =============================================================================
# 优先级标签
# =============================================================================
echo "创建优先级标签..."

gh label create "priority:urgent" \
    --repo "$REPO" \
    --color "FF0000" \
    --description "紧急 - 需2小时内审查" \
    --force || true

gh label create "priority:high" \
    --repo "$REPO" \
    --color "FF6600" \
    --description "高优先级 - 需4小时内审查" \
    --force || true

gh label create "priority:normal" \
    --repo "$REPO" \
    --color "FBCA04" \
    --description "正常优先级 - 需24小时内审查" \
    --force || true

gh label create "priority:low" \
    --repo "$REPO" \
    --color "C2E0C6" \
    --description "低优先级 - 可延后审查" \
    --force || true

echo ""
echo "✅ 所有代码审查标签创建完成！"
echo ""
echo "标签分类："
echo "  审查意见: review:must-fix, review:suggest, review:comment"
echo "  变更类型: type:feat, type:fix, type:refactor, type:security, type:perf, type:docs, type:test, type:config, type:migration"
echo "  影响范围: scope:backend, scope:frontend, scope:fullstack, scope:infra, scope:security, scope:database"
echo "  优先级:   priority:urgent, priority:high, priority:normal, priority:low"
