#!/usr/bin/env bash
# =============================================================================
# SOC Copilot - GitHub 分支保护规则配置脚本
#
# 功能：通过 GitHub API 设置 main 和 develop 分支的保护规则
# 用法：./scripts/setup-branch-protection.sh [--dry-run] [--repo OWNER/REPO]
#
# 前置条件：
#   - GitHub CLI (gh) 已安装并认证
#   - 具有 repo 管理权限的 GitHub Token
#   - 仓库已存在 main 和 develop 分支
#
# 关联需求：FR-001（分支策略管理）
# =============================================================================

set -euo pipefail

# ======================== 配置 ========================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
RULES_FILE="$PROJECT_ROOT/.github/branch-protection-rules.json"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ======================== 参数解析 ========================

DRY_RUN=false
REPO=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --repo)
            REPO="$2"
            shift 2
            ;;
        --help|-h)
            echo "用法: $0 [--dry-run] [--repo OWNER/REPO]"
            echo ""
            echo "选项:"
            echo "  --dry-run         仅显示将要执行的API调用，不实际执行"
            echo "  --repo OWNER/REPO 指定GitHub仓库（默认从git remote自动检测）"
            echo "  --help, -h        显示此帮助信息"
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

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# ======================== 前置检查 ========================

check_prerequisites() {
    log_info "检查前置条件..."

    # 检查 gh CLI
    if ! command -v gh &> /dev/null; then
        log_error "GitHub CLI (gh) 未安装。请访问 https://cli.github.com/ 安装。"
        exit 1
    fi

    # 检查 gh 认证状态
    if ! gh auth status &> /dev/null; then
        log_error "GitHub CLI 未认证。请运行 'gh auth login' 进行认证。"
        exit 1
    fi
    log_success "GitHub CLI 已认证"

    # 检查规则配置文件
    if [[ ! -f "$RULES_FILE" ]]; then
        log_error "分支保护规则配置文件不存在: $RULES_FILE"
        exit 1
    fi
    log_success "规则配置文件已找到: $RULES_FILE"

    # 检查 jq
    if ! command -v jq &> /dev/null; then
        log_error "jq 未安装。请运行 'brew install jq' 安装。"
        exit 1
    fi
    log_success "jq 已安装"
}

# 自动检测仓库
detect_repo() {
    if [[ -n "$REPO" ]]; then
        echo "$REPO"
        return
    fi

    local remote_url
    remote_url=$(cd "$PROJECT_ROOT" && git remote get-url origin 2>/dev/null || echo "")

    if [[ -z "$remote_url" ]]; then
        log_error "无法检测 Git remote。请使用 --repo 参数指定仓库。"
        exit 1
    fi

    # 从 remote URL 提取 OWNER/REPO
    # 支持 https://github.com/OWNER/REPO.git 和 git@github.com:OWNER/REPO.git
    local repo_path
    repo_path=$(echo "$remote_url" | sed -E 's|.*github.com[:/]([^/]+/[^/]+)(\.git)?$|\1|')
    echo "$repo_path"
}

# ======================== 分支保护规则配置 ========================

setup_branch_protection() {
    local branch=$1
    local repo=$2

    log_info "配置分支 '$branch' 的保护规则..."

    # 从 JSON 配置文件读取规则
    local enforce_admins
    enforce_admins=$(jq -r ".branch_protection_rules.\"$branch\".enforce_admins" "$RULES_FILE")

    local required_approving_review_count
    required_approving_review_count=$(jq -r ".branch_protection_rules.\"$branch\".required_pull_request_reviews.required_approving_review_count" "$RULES_FILE")

    local dismiss_stale_reviews
    dismiss_stale_reviews=$(jq -r ".branch_protection_rules.\"$branch\".required_pull_request_reviews.dismiss_stale_reviews" "$RULES_FILE")

    local require_code_owner_reviews
    require_code_owner_reviews=$(jq -r ".branch_protection_rules.\"$branch\".required_pull_request_reviews.require_code_owner_reviews" "$RULES_FILE")

    local required_linear_history
    required_linear_history=$(jq -r ".branch_protection_rules.\"$branch\".required_linear_history" "$RULES_FILE")

    local allow_force_pushes
    allow_force_pushes=$(jq -r ".branch_protection_rules.\"$branch\".allow_force_pushes" "$RULES_FILE")

    local allow_deletions
    allow_deletions=$(jq -r ".branch_protection_rules.\"$branch\".allow_deletions" "$RULES_FILE")

    local required_conversation_resolution
    required_conversation_resolution=$(jq -r ".branch_protection_rules.\"$branch\".required_conversation_resolution" "$RULES_FILE")

    # 读取状态检查上下文
    local status_checks
    status_checks=$(jq -r ".branch_protection_rules.\"$branch\".required_status_checks.contexts[]" "$RULES_FILE" | tr '\n' ',' | sed 's/,$//')

    local strict_status_checks
    strict_status_checks=$(jq -r ".branch_protection_rules.\"$branch\".required_status_checks.strict" "$RULES_FILE")

    # 构建 GitHub API payload
    local payload
    payload=$(jq -n \
        --argjson enforce_admins "$enforce_admins" \
        --argjson required_approving_review_count "$required_approving_review_count" \
        --argjson dismiss_stale_reviews "$dismiss_stale_reviews" \
        --argjson require_code_owner_reviews "$require_code_owner_reviews" \
        --argjson required_linear_history "$required_linear_history" \
        --argjson allow_force_pushes "$allow_force_pushes" \
        --argjson allow_deletions "$allow_deletions" \
        --argjson required_conversation_resolution "$required_conversation_resolution" \
        --argjson strict "$strict_status_checks" \
        --arg status_checks "$status_checks" \
        '{
            enforce_admins: $enforce_admins,
            required_pull_request_reviews: {
                dismiss_stale_reviews: $dismiss_stale_reviews,
                require_code_owner_reviews: $require_code_owner_reviews,
                required_approving_review_count: $required_approving_review_count
            },
            required_status_checks: {
                strict: $strict,
                contexts: ($status_checks | split(","))
            },
            restrictions: null,
            required_linear_history: $required_linear_history,
            allow_force_pushes: $allow_force_pushes,
            allow_deletions: $allow_deletions,
            required_conversation_resolution: $required_conversation_resolution
        }'
    )

    if [[ "$DRY_RUN" == true ]]; then
        log_warn "[DRY-RUN] 将对仓库 $repo 分支 $branch 设置以下保护规则:"
        echo "$payload" | jq '.'
        return
    fi

    # 调用 GitHub API 设置分支保护规则
    local api_response
    api_response=$(gh api \
        "repos/$repo/branches/$branch/protection" \
        --method PUT \
        --input - <<EOF
$payload
EOF
    2>&1) || true

    if echo "$api_response" | jq -e '.url' &> /dev/null; then
        log_success "分支 '$branch' 保护规则设置成功"
    else
        log_error "分支 '$branch' 保护规则设置失败"
        echo "$api_response"
        return 1
    fi
}

# ======================== 主流程 ========================

main() {
    echo "============================================"
    echo " SOC Copilot - GitHub 分支保护规则配置"
    echo "============================================"
    echo ""

    check_prerequisites

    local repo
    repo=$(detect_repo)
    log_info "目标仓库: $repo"

    # 检查仓库是否可访问
    if [[ "$DRY_RUN" != true ]]; then
        if ! gh repo view "$repo" &> /dev/null; then
            log_error "无法访问仓库 $repo。请检查权限。"
            exit 1
        fi
        log_success "仓库可访问"
    fi

    echo ""
    log_info "开始配置分支保护规则..."
    echo ""

    local success_count=0
    local fail_count=0

    # 配置 main 分支保护规则
    if setup_branch_protection "main" "$repo"; then
        ((success_count++))
    else
        ((fail_count++))
    fi

    echo ""

    # 配置 develop 分支保护规则
    if setup_branch_protection "develop" "$repo"; then
        ((success_count++))
    else
        ((fail_count++))
    fi

    echo ""
    echo "============================================"
    echo " 配置完成"
    echo "============================================"
    echo -e "  ${GREEN}成功: $success_count${NC}"
    echo -e "  ${RED}失败: $fail_count${NC}"
    echo ""

    if [[ $fail_count -gt 0 ]]; then
        log_warn "部分分支保护规则设置失败，请检查错误信息。"
        log_warn "常见原因："
        log_warn "  1. 分支不存在（需先创建 develop 分支）"
        log_warn "  2. GitHub Token 权限不足"
        log_warn "  3. 仓库使用免费版，部分功能受限"
        exit 1
    fi

    log_success "所有分支保护规则已配置完成！"
    echo ""
    log_info "提示：可通过以下命令查看当前保护规则："
    echo "  gh api repos/$repo/branches/main/protection"
    echo "  gh api repos/$repo/branches/develop/protection"
}

main
