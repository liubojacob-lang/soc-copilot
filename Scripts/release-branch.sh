#!/usr/bin/env bash
# =============================================================================
# SOC Copilot - 发布分支管理脚本
# 管理 release 分支的创建、合并回 develop、清理等操作
# 关联需求：FR-003（版本发布流程管理）
# =============================================================================

set -euo pipefail

# ─── 颜色输出 ────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

info()    { echo -e "${BLUE}[INFO]${NC} $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC} $*"; }
error()   { echo -e "${RED}[ERROR]${NC} $*"; exit 1; }
success() { echo -e "${GREEN}[OK]${NC} $*"; }
section() { echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"; echo -e "${CYAN}$*${NC}"; echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"; }

# ─── 帮助信息 ────────────────────────────────────────────────
usage() {
    cat <<EOF
SOC Copilot - 发布分支管理工具

用法:
  $0 <command> [options]

命令:
  start <version>    创建 release 分支并更新版本号
  finish <version>   合并 release 分支回 develop 并清理
  status [version]   查看 release 分支状态
  list               列出所有 release 分支
  abort <version>    中止发布，删除 release 分支

选项:
  --dry-run          预览模式: 显示操作但不执行
  --no-bump          start 时不自动更新版本号
  --no-changelog     start 时不自动生成 CHANGELOG
  --no-delete        finish 时不删除 release 分支
  -h, --help         显示帮助信息

示例:
  $0 start 0.10.0                  # 创建 release/v0.10.0 分支
  $0 start 0.10.0 --dry-run        # 预览创建操作
  $0 finish 0.10.0                  # 完成 v0.10.0 发布
  $0 status                         # 查看当前 release 分支状态
  $0 list                           # 列出所有 release 分支
  $0 abort 0.10.0                   # 中止 v0.10.0 发布

发布流程:
  1. start: develop → release/vX.Y.Z (版本号更新 + CHANGELOG)
  2. 在 release 分支上修复 Bug
  3. finish: release/vX.Y.Z → main (创建 PR)
  4. 合并后: release/vX.Y.Z → develop + 清理
EOF
    exit 0
}

# ─── 参数解析 ────────────────────────────────────────────────
COMMAND=""
VERSION=""
DRY_RUN=false
NO_BUMP=false
NO_CHANGELOG=false
NO_DELETE=false

if [[ $# -lt 1 ]]; then
    usage
fi

COMMAND="$1"
shift

case "$COMMAND" in
    start|finish|status|list|abort)
        ;;
    -h|--help)
        usage
        ;;
    *)
        error "未知命令: $COMMAND (使用 -h 查看帮助)"
        ;;
esac

# 解析版本号和选项
if [[ "$COMMAND" != "list" ]]; then
    if [[ $# -lt 1 ]] && [[ "$COMMAND" != "status" ]]; then
        error "命令 '$COMMAND' 需要指定版本号"
    fi
    if [[ $# -ge 1 ]] && [[ ! "$1" =~ ^-- ]]; then
        VERSION="$1"
        shift
    fi
fi

while [[ $# -gt 0 ]]; do
    case "$1" in
        --dry-run)       DRY_RUN=true; shift ;;
        --no-bump)       NO_BUMP=true; shift ;;
        --no-changelog)  NO_CHANGELOG=true; shift ;;
        --no-delete)     NO_DELETE=false; shift ;;  # 注意这里原来是 NO_DELETE=true，但逻辑应该是 finish 时不删除
        -h|--help)       usage ;;
        *)               error "未知参数: $1" ;;
    esac
done

# ─── 修正参数 ────────────────────────────────────────────────
# --no-delete 意味着 finish 时不删除分支
NO_DELETE_VAL=false
# 重新解析一次来修正
for arg in "$@"; do
    if [[ "$arg" == "--no-delete" ]]; then
        NO_DELETE_VAL=true
    fi
done

# ─── 工具函数 ────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

validate_version() {
    if ! echo "$VERSION" | grep -qE '^[0-9]+\.[0-9]+\.[0-9]+(-[a-zA-Z0-9.]+)?$'; then
        error "无效的版本号格式: $VERSION (期望: MAJOR.MINOR.PATCH[-prerelease])"
    fi
}

get_current_branch() {
    git rev-parse --abbrev-ref HEAD
}

branch_exists() {
    git branch --list "$1" | grep -q "$1" || git branch -r --list "origin/$1" | grep -q "$1"
}

ensure_clean_working_tree() {
    if ! git diff --quiet 2>/dev/null || ! git diff --cached --quiet 2>/dev/null; then
        error "工作区有未提交的变更，请先提交或暂存后再执行此操作"
    fi
}

# ─── 命令: start ────────────────────────────────────────────
cmd_start() {
    validate_version
    local branch="release/v${VERSION}"

    section "🚀 创建发布分支 v${VERSION}"

    # 前置检查
    if branch_exists "$branch"; then
        error "分支 $branch 已存在"
    fi

    ensure_clean_working_tree

    local current_branch
    current_branch=$(get_current_branch)

    # 检查是否在 develop 分支
    if [[ "$current_branch" != "develop" ]]; then
        warn "当前不在 develop 分支 (当前: $current_branch)"
        if [[ "$DRY_RUN" != "true" ]]; then
            info "切换到 develop 分支..."
            git checkout develop || error "切换到 develop 失败"
        fi
    fi

    # 拉取最新代码
    if [[ "$DRY_RUN" != "true" ]]; then
        info "拉取 develop 最新代码..."
        git pull origin develop || warn "拉取失败，继续使用本地代码"
    fi

    # 创建 release 分支
    if [[ "$DRY_RUN" == "true" ]]; then
        info "[DRY-RUN] git checkout -b $branch"
    else
        git checkout -b "$branch"
        success "已创建分支: $branch"
    fi

    # 更新版本号
    if [[ "$NO_BUMP" != "true" ]]; then
        info "更新版本号..."
        if [[ "$DRY_RUN" == "true" ]]; then
            info "[DRY-RUN] ./scripts/bump-version.sh $VERSION"
        else
            "$SCRIPT_DIR/bump-version.sh" "$VERSION" --no-commit
            git add "$PROJECT_ROOT/backend/pyproject.toml" "$PROJECT_ROOT/frontend/package.json"
            git commit -m "chore(release): bump version to v${VERSION}"
            success "版本号已更新并提交: v${VERSION}"
        fi
    fi

    # 生成 CHANGELOG
    if [[ "$NO_CHANGELOG" != "true" ]]; then
        info "生成 CHANGELOG..."
        if [[ "$DRY_RUN" == "true" ]]; then
            info "[DRY-RUN] ./scripts/generate-changelog.sh $VERSION"
        else
            "$SCRIPT_DIR/generate-changelog.sh" "$VERSION"
            git add "$PROJECT_ROOT/CHANGELOG.md"
            git commit -m "docs(changelog): update for v${VERSION}" || warn "CHANGELOG 无变更"
            success "CHANGELOG 已更新"
        fi
    fi

    # 推送远程
    if [[ "$DRY_RUN" == "true" ]]; then
        info "[DRY-RUN] git push origin $branch"
    else
        git push -u origin "$branch"
        success "已推送到远程: origin/$branch"
    fi

    echo ""
    success "✅ 发布分支创建完成: $branch"
    echo ""
    info "下一步:"
    info "  1. 确认 CI 检查通过"
    info "  2. 创建 PR: $branch → main (使用 release.md 模板)"
    info "  3. 等待项目负责人审批"
    info "  4. 合并后自动触发发布工作流"
}

# ─── 命令: finish ───────────────────────────────────────────
cmd_finish() {
    validate_version
    local branch="release/v${VERSION}"

    section "🏁 完成发布 v${VERSION}"

    # 前置检查
    ensure_clean_working_tree

    local current_branch
    current_branch=$(get_current_branch)

    # 切换到 develop
    if [[ "$DRY_RUN" == "true" ]]; then
        info "[DRY-RUN] git checkout develop"
    else
        git checkout develop || error "切换到 develop 失败"
        git pull origin develop || warn "拉取 develop 失败"
    fi

    # 合并 release 到 develop
    if ! branch_exists "$branch"; then
        error "分支 $branch 不存在"
    fi

    if [[ "$DRY_RUN" == "true" ]]; then
        info "[DRY-RUN] git merge $branch --no-ff -m 'Merge $branch into develop'"
    else
        git merge "$branch" --no-ff -m "Merge $branch into develop" || {
            error "合并冲突！请手动解决冲突后执行: git add . && git commit && git push"
        }
        git push origin develop
        success "已合并 $branch → develop"
    fi

    # 删除 release 分支
    if [[ "$NO_DELETE_VAL" != "true" ]]; then
        if [[ "$DRY_RUN" == "true" ]]; then
            info "[DRY-RUN] git branch -d $branch"
            info "[DRY-RUN] git push origin --delete $branch"
        else
            git branch -d "$branch" 2>/dev/null || warn "本地分支 $branch 删除失败（可能已删除）"
            git push origin --delete "$branch" 2>/dev/null || warn "远程分支 $branch 删除失败（可能已删除）"
            success "已清理 release 分支: $branch"
        fi
    else
        info "保留 release 分支（--no-delete）"
    fi

    echo ""
    success "✅ 发布完成: v${VERSION}"
}

# ─── 命令: status ───────────────────────────────────────────
cmd_status() {
    section "📊 发布分支状态"

    # 当前版本
    local current_version
    if [[ -f "$PROJECT_ROOT/backend/pyproject.toml" ]]; then
        current_version=$(grep '^version = ' "$PROJECT_ROOT/backend/pyproject.toml" | head -1 | sed 's/version = "\(.*\)"/\1/')
    else
        current_version="unknown"
    fi

    echo "当前版本: v$current_version"
    echo "当前分支: $(get_current_branch)"
    echo ""

    # Release 分支状态
    local release_branches
    release_branches=$(git branch --list 'release/*' 2>/dev/null || echo "")

    if [[ -n "$release_branches" ]]; then
        echo "活跃的 release 分支:"
        while IFS= read -r branch; do
            branch=$(echo "$branch" | tr -d ' *')
            if [[ -n "$branch" ]]; then
                local last_commit
                last_commit=$(git log -1 --format="%h %s (%cr)" "$branch" 2>/dev/null || echo "unknown")
                echo "  📦 $branch"
                echo "     最后提交: $last_commit"
            fi
        done <<< "$release_branches"
    else
        echo "没有活跃的 release 分支"
    fi

    echo ""

    # 最近的标签
    echo "最近的版本标签:"
    git tag --sort=-version:refname | grep -E '^v[0-9]' | head -5 | while read -r tag; do
        local tag_date
        tag_date=$(git log -1 --format="%ai" "$tag" 2>/dev/null || echo "unknown")
        echo "  🏷️  $tag ($tag_date)"
    done || echo "  (无版本标签)"

    # 指定版本的状态
    if [[ -n "$VERSION" ]]; then
        echo ""
        echo "版本 v${VERSION} 详细状态:"
        local branch="release/v${VERSION}"
        local tag="v${VERSION}"

        if branch_exists "$branch"; then
            echo "  📦 Release 分支: 存在"
        else
            echo "  📦 Release 分支: 不存在"
        fi

        if git tag -l "$tag" | grep -q "$tag"; then
            echo "  🏷️  Git 标签: 已创建"
        else
            echo "  🏷️  Git 标签: 未创建"
        fi

        # 检查 GitHub Release (需要 gh CLI)
        if command -v gh &>/dev/null; then
            if gh release view "$tag" &>/dev/null; then
                echo "  📋 GitHub Release: 已发布"
            else
                echo "  📋 GitHub Release: 未发布"
            fi
        fi
    fi
}

# ─── 命令: list ─────────────────────────────────────────────
cmd_list() {
    section "📋 Release 分支列表"

    echo "本地 release 分支:"
    local local_branches
    local_branches=$(git branch --list 'release/*' 2>/dev/null || echo "")
    if [[ -n "$local_branches" ]]; then
        echo "$local_branches" | while read -r branch; do
            echo "  $branch"
        done
    else
        echo "  (无)"
    fi

    echo ""
    echo "远程 release 分支:"
    local remote_branches
    remote_branches=$(git branch -r --list 'origin/release/*' 2>/dev/null || echo "")
    if [[ -n "$remote_branches" ]]; then
        echo "$remote_branches" | while read -r branch; do
            echo "  $branch"
        done
    else
        echo "  (无)"
    fi

    echo ""
    echo "版本标签:"
    git tag -l 'v*' --sort=-version:refname | head -10 | while read -r tag; do
        echo "  $tag"
    done || echo "  (无)"
}

# ─── 命令: abort ────────────────────────────────────────────
cmd_abort() {
    validate_version
    local branch="release/v${VERSION}"

    section "🚨 中止发布 v${VERSION}"

    # 确认操作
    echo "⚠️  即将删除发布分支: $branch"
    echo "⚠️  此操作不可逆！"
    echo ""
    read -rp "确认中止发布 v${VERSION}? [y/N] " confirm
    if [[ "$confirm" != "y" && "$confirm" != "Y" ]]; then
        info "操作已取消"
        exit 0
    fi

    # 切换到 develop
    if [[ "$DRY_RUN" == "true" ]]; then
        info "[DRY-RUN] git checkout develop"
    else
        git checkout develop 2>/dev/null || warn "切换到 develop 失败"
    fi

    # 删除本地分支
    if [[ "$DRY_RUN" == "true" ]]; then
        info "[DRY-RUN] git branch -D $branch"
    else
        git branch -D "$branch" 2>/dev/null || warn "本地分支 $branch 不存在"
    fi

    # 删除远程分支
    if [[ "$DRY_RUN" == "true" ]]; then
        info "[DRY-RUN] git push origin --delete $branch"
    else
        git push origin --delete "$branch" 2>/dev/null || warn "远程分支 $branch 不存在"
    fi

    echo ""
    success "✅ 发布已中止: v${VERSION}"
    info "已切换回 develop 分支，可以继续开发"
}

# ─── 主流程 ──────────────────────────────────────────────────
main() {
    if ! git rev-parse --is-inside-work-tree &>/dev/null; then
        error "当前目录不是 Git 仓库"
    fi

    case "$COMMAND" in
        start)   cmd_start ;;
        finish)  cmd_finish ;;
        status)  cmd_status ;;
        list)    cmd_list ;;
        abort)   cmd_abort ;;
    esac
}

main
