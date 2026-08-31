#!/usr/bin/env bash
# =============================================================================
# SOC Copilot - 版本号递增脚本
# 支持 MAJOR/MINOR/PATCH 递增，同步更新 pyproject.toml 和 package.json
# 关联需求：FR-003（版本发布流程管理）
# =============================================================================

set -euo pipefail

# ─── 颜色输出 ────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

info()  { echo -e "${BLUE}[INFO]${NC} $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*"; exit 1; }
success() { echo -e "${GREEN}[OK]${NC} $*"; }

# ─── 帮助信息 ────────────────────────────────────────────────
usage() {
    cat <<EOF
SOC Copilot - 版本号递增工具

用法:
  $0 <version|bump-type> [options]

参数:
  version        目标版本号 (如: 0.10.0)
  bump-type      递增类型: major, minor, patch

选项:
  --dry-run      预览模式: 显示变更但不修改文件
  --no-commit    不自动创建 Git 提交
  --no-tag       不自动创建 Git 标签
  -h, --help     显示帮助信息

示例:
  $0 0.10.0                      # 设置版本号为 0.10.0
  $0 minor                        # 递增 MINOR 版本 (0.9.0 → 0.10.0)
  $0 patch                        # 递增 PATCH 版本 (0.9.0 → 0.9.1)
  $0 major                        # 递增 MAJOR 版本 (0.9.0 → 1.0.0)
  $0 0.10.0 --dry-run             # 预览变更
  $0 minor --no-commit            # 递增但不提交

版本号文件:
  - backend/pyproject.toml   → version = "X.Y.Z"
  - frontend/package.json    → "version": "X.Y.Z"
EOF
    exit 0
}

# ─── 参数解析 ────────────────────────────────────────────────
TARGET=""
DRY_RUN=false
AUTO_COMMIT=true
AUTO_TAG=false

if [[ $# -lt 1 ]]; then
    usage
fi

# 处理第一个参数为 --help 的情况
if [[ "$1" == "-h" || "$1" == "--help" ]]; then
    usage
fi

TARGET="$1"
shift

while [[ $# -gt 0 ]]; do
    case "$1" in
        --dry-run)    DRY_RUN=true; shift ;;
        --no-commit)  AUTO_COMMIT=false; shift ;;
        --no-tag)     AUTO_TAG=false; shift ;;
        -h|--help)    usage ;;
        *)            error "未知参数: $1" ;;
    esac
done

# ─── 文件路径 ────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PYPROJECT="$PROJECT_ROOT/backend/pyproject.toml"
PACKAGE_JSON="$PROJECT_ROOT/frontend/package.json"

# ─── 获取当前版本号 ──────────────────────────────────────────
get_current_version() {
    local py_ver
    py_ver=$(grep '^version = ' "$PYPROJECT" | head -1 | sed 's/version = "\(.*\)"/\1/')
    echo "$py_ver"
}

# ─── 计算新版本号 ────────────────────────────────────────────
calculate_new_version() {
    local current="$1"
    local target="$2"

    local major minor patch
    IFS='.' read -r major minor patch <<< "$current"

    case "$target" in
        major)
            major=$((major + 1))
            minor=0
            patch=0
            ;;
        minor)
            minor=$((minor + 1))
            patch=0
            ;;
        patch)
            patch=$((patch + 1))
            ;;
        *)
            # 直接设置版本号
            if ! echo "$target" | grep -qE '^[0-9]+\.[0-9]+\.[0-9]+(-[a-zA-Z0-9.]+)?$'; then
                error "无效的版本号或递增类型: $target"
            fi
            echo "$target"
            return
            ;;
    esac

    echo "${major}.${minor}.${patch}"
}

# ─── 更新 pyproject.toml ────────────────────────────────────
update_pyproject() {
    local new_version="$1"

    if [[ "$DRY_RUN" == "true" ]]; then
        info "[DRY-RUN] 更新 $PYPROJECT: version = \"$new_version\""
        return
    fi

    if [[ ! -f "$PYPROJECT" ]]; then
        error "文件不存在: $PYPROJECT"
    fi

    # 使用 sed 更新版本号
    if [[ "$(uname)" == "Darwin" ]]; then
        sed -i '' "s/^version = \".*\"/version = \"$new_version\"/" "$PYPROJECT"
    else
        sed -i "s/^version = \".*\"/version = \"$new_version\"/" "$PYPROJECT"
    fi

    success "已更新 pyproject.toml: version = \"$new_version\""
}

# ─── 更新 package.json ──────────────────────────────────────
update_package_json() {
    local new_version="$1"

    if [[ "$DRY_RUN" == "true" ]]; then
        info "[DRY-RUN] 更新 $PACKAGE_JSON: \"version\": \"$new_version\""
        return
    fi

    if [[ ! -f "$PACKAGE_JSON" ]]; then
        error "文件不存在: $PACKAGE_JSON"
    fi

    # 使用 sed 更新版本号（匹配 "version": "X.Y.Z" 格式）
    if [[ "$(uname)" == "Darwin" ]]; then
        sed -i '' "s/\"version\": \"[0-9][0-9.]*[a-zA-Z0-9.-]*\"/\"version\": \"$new_version\"/" "$PACKAGE_JSON"
    else
        sed -i "s/\"version\": \"[0-9][0-9.]*[a-zA-Z0-9.-]*\"/\"version\": \"$new_version\"/" "$PACKAGE_JSON"
    fi

    success "已更新 package.json: \"version\": \"$new_version\""
}

# ─── 验证版本一致性 ──────────────────────────────────────────
verify_version_consistency() {
    local expected="$1"

    local py_ver pkg_ver
    py_ver=$(grep '^version = ' "$PYPROJECT" | head -1 | sed 's/version = "\(.*\)"/\1/')
    pkg_ver=$(grep '"version"' "$PACKAGE_JSON" | head -1 | sed 's/.*"version": "\(.*\)".*/\1/')

    info "版本一致性验证:"
    info "  期望版本: $expected"
    info "  pyproject.toml: $py_ver"
    info "  package.json: $pkg_ver"

    if [[ "$py_ver" != "$expected" ]]; then
        error "pyproject.toml 版本号不一致: $py_ver ≠ $expected"
    fi

    if [[ "$pkg_ver" != "$expected" ]]; then
        error "package.json 版本号不一致: $pkg_ver ≠ $expected"
    fi

    success "版本号一致性验证通过"
}

# ─── Git 提交 ────────────────────────────────────────────────
git_commit() {
    local new_version="$1"

    if [[ "$DRY_RUN" == "true" ]]; then
        info "[DRY-RUN] Git commit: chore(release): bump version to v$new_version"
        return
    fi

    if [[ "$AUTO_COMMIT" != "true" ]]; then
        info "跳过自动提交（--no-commit）"
        return
    fi

    # 检查是否有变更
    if git diff --quiet "$PYPROJECT" "$PACKAGE_JSON" 2>/dev/null; then
        warn "没有文件变更，跳过提交"
        return
    fi

    git add "$PYPROJECT" "$PACKAGE_JSON"
    git commit -m "chore(release): bump version to v$new_version"

    success "已提交版本号变更: v$new_version"
}

# ─── Git 标签 ────────────────────────────────────────────────
git_tag() {
    local new_version="$1"

    if [[ "$DRY_RUN" == "true" ]]; then
        info "[DRY-RUN] Git tag: v$new_version"
        return
    fi

    if [[ "$AUTO_TAG" != "true" ]]; then
        info "跳过自动标签（默认不创建标签，由 CI 工作流创建）"
        return
    fi

    if git tag -l "v$new_version" | grep -q "v$new_version"; then
        warn "标签 v$new_version 已存在，跳过"
        return
    fi

    git tag -a "v$new_version" -m "Release v$new_version"
    success "已创建标签: v$new_version"
}

# ─── 主流程 ──────────────────────────────────────────────────
main() {
    # 验证 git 仓库
    if ! git rev-parse --is-inside-work-tree &>/dev/null; then
        error "当前目录不是 Git 仓库"
    fi

    # 获取当前版本
    local current_version
    current_version=$(get_current_version)
    info "当前版本: v$current_version"

    # 计算新版本
    local new_version
    new_version=$(calculate_new_version "$current_version" "$TARGET")
    info "目标版本: v$new_version"

    # 确认版本变更
    if [[ "$current_version" == "$new_version" ]]; then
        warn "版本号未变更: v$current_version"
        exit 0
    fi

    echo ""
    info "版本递增: v$current_version → v$new_version"
    echo ""

    # 更新文件
    update_pyproject "$new_version"
    update_package_json "$new_version"

    # 验证
    if [[ "$DRY_RUN" != "true" ]]; then
        verify_version_consistency "$new_version"
    fi

    # Git 操作
    git_commit "$new_version"
    git_tag "$new_version"

    echo ""
    success "✅ 版本号已更新: v$current_version → v$new_version"

    if [[ "$DRY_RUN" != "true" ]]; then
        echo ""
        info "下一步:"
        info "  1. 运行 'make release-changelog VER=$new_version' 生成 CHANGELOG"
        info "  2. 运行 'git push origin release/v$new_version' 推送变更"
        info "  3. 创建发布 PR 合并到 main"
    fi
}

main
