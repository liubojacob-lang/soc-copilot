#!/usr/bin/env bash
# =============================================================================
# SOC Copilot - Git 分支命名规范验证脚本
#
# 功能：验证当前 Git 分支名称是否符合项目命名规范
# 用法：./scripts/validate-branch-name.sh [--branch BRANCH_NAME]
#
# 分支命名规范：
#   - main                          永久分支
#   - develop                       永久分支
#   - feature/FR-xxx-简短描述       功能分支
#   - fix/FR-xxx-简短描述           修复分支
#   - release/vX.Y.Z               发布分支
#   - hotfix/vX.Y.Z-简短描述       热修复分支
#
# 关联需求：FR-001（分支策略管理）
# =============================================================================

set -euo pipefail

# ======================== 配置 ========================

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ======================== 参数解析 ========================

BRANCH_NAME=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --branch)
            BRANCH_NAME="$2"
            shift 2
            ;;
        --help|-h)
            echo "用法: $0 [--branch BRANCH_NAME]"
            echo ""
            echo "选项:"
            echo "  --branch NAME  指定要验证的分支名（默认为当前分支）"
            echo "  --help, -h     显示此帮助信息"
            echo ""
            echo "分支命名规范:"
            echo "  main                           永久分支"
            echo "  develop                        永久分支"
            echo "  feature/FR-xxx-简短描述        功能分支"
            echo "  fix/FR-xxx-简短描述            修复分支"
            echo "  release/vX.Y.Z                 发布分支"
            echo "  hotfix/vX.Y.Z-简短描述         热修复分支"
            exit 0
            ;;
        *)
            echo -e "${RED}错误: 未知参数 $1${NC}"
            exit 1
            ;;
    esac
done

# ======================== 工具函数 ========================

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[OK]${NC} $1"
}

log_error() {
    echo -e "${RED}[FAIL]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

# ======================== 验证逻辑 ========================

# 获取分支名
if [[ -z "$BRANCH_NAME" ]]; then
    # 检查是否在 Git 仓库中
    if ! git rev-parse --is-inside-work-tree &> /dev/null; then
        log_error "不在 Git 仓库中"
        exit 1
    fi

    BRANCH_NAME=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "")

    if [[ -z "$BRANCH_NAME" ]]; then
        log_error "无法获取当前分支名（可能处于 detached HEAD 状态）"
        exit 1
    fi
fi

log_info "验证分支名: $BRANCH_NAME"

# 定义正则表达式
PERMANENT_BRANCH_REGEX='^(main|develop)$'
FEATURE_BRANCH_REGEX='^feature/FR-[0-9]+-[a-z][a-z0-9-]+$'
FIX_BRANCH_REGEX='^fix/FR-[0-9]+-[a-z][a-z0-9-]+$'
RELEASE_BRANCH_REGEX='^release/v[0-9]+\.[0-9]+\.[0-9]+$'
HOTFIX_BRANCH_REGEX='^hotfix/v[0-9]+\.[0-9]+\.[0-9]+-[a-z][a-z0-9-]+$'

# 验证结果
IS_VALID=false
BRANCH_TYPE=""

if [[ "$BRANCH_NAME" =~ $PERMANENT_BRANCH_REGEX ]]; then
    IS_VALID=true
    BRANCH_TYPE="永久分支"
elif [[ "$BRANCH_NAME" =~ $FEATURE_BRANCH_REGEX ]]; then
    IS_VALID=true
    BRANCH_TYPE="功能分支 (feature)"
elif [[ "$BRANCH_NAME" =~ $FIX_BRANCH_REGEX ]]; then
    IS_VALID=true
    BRANCH_TYPE="修复分支 (fix)"
elif [[ "$BRANCH_NAME" =~ $RELEASE_BRANCH_REGEX ]]; then
    IS_VALID=true
    BRANCH_TYPE="发布分支 (release)"
elif [[ "$BRANCH_NAME" =~ $HOTFIX_BRANCH_REGEX ]]; then
    IS_VALID=true
    BRANCH_TYPE="热修复分支 (hotfix)"
fi

# ======================== 输出结果 ========================

echo ""
if [[ "$IS_VALID" == true ]]; then
    log_success "分支名 '$BRANCH_NAME' 符合命名规范"
    echo "  类型: $BRANCH_TYPE"
    echo ""
    exit 0
else
    log_error "分支名 '$BRANCH_NAME' 不符合命名规范！"
    echo ""
    echo "  正确的命名格式："
    echo "    main                           永久分支"
    echo "    develop                        永久分支"
    echo "    feature/FR-xxx-简短描述        功能分支 (如: feature/FR-001-alert-dedup)"
    echo "    fix/FR-xxx-简短描述             修复分支 (如: fix/FR-002-login-timeout)"
    echo "    release/vX.Y.Z                 发布分支 (如: release/v0.10.0)"
    echo "    hotfix/vX.Y.Z-简短描述          热修复分支 (如: hotfix/v0.10.1-xss-fix)"
    echo ""

    # 给出具体建议
    if [[ "$BRANCH_NAME" == feature/* ]]; then
        log_warn "建议: feature 分支需包含需求编号，格式为 feature/FR-xxx-描述"
    elif [[ "$BRANCH_NAME" == fix/* ]]; then
        log_warn "建议: fix 分支需包含需求编号，格式为 fix/FR-xxx-描述"
    elif [[ "$BRANCH_NAME" == release/* ]]; then
        log_warn "建议: release 分支需使用语义化版本号，格式为 release/vX.Y.Z"
    elif [[ "$BRANCH_NAME" == hotfix/* ]]; then
        log_warn "建议: hotfix 分支需使用语义化版本号加描述，格式为 hotfix/vX.Y.Z-描述"
    elif [[ "$BRANCH_NAME" =~ [A-Z] ]]; then
        log_warn "建议: 分支名应全部使用小写字母"
    elif [[ "$BRANCH_NAME" =~ _ ]]; then
        log_warn "建议: 分支名应使用连字符(-)而非下划线(_)"
    fi

    echo ""
    log_error "请重命名分支: git branch -m $BRANCH_NAME <正确名称>"
    exit 1
fi
