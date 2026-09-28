#!/usr/bin/env bash
# =============================================================================
# SOC Copilot - CHANGELOG 自动生成脚本
# 基于 Git conventional commits 和标签生成变更日志
# 关联需求：FR-003（版本发布流程管理）
# =============================================================================

set -euo pipefail

# ─── 颜色输出 ────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

info()  { echo -e "${BLUE}[INFO]${NC} $*" >&2; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $*" >&2; }
error() { echo -e "${RED}[ERROR]${NC} $*" >&2; exit 1; }
success() { echo -e "${GREEN}[OK]${NC} $*" >&2; }

# ─── 帮助信息 ────────────────────────────────────────────────
usage() {
    cat <<EOF
SOC Copilot - CHANGELOG 自动生成工具

用法:
  $0 <version> [options]

参数:
  version          目标版本号 (如: 0.10.0)

选项:
  --ci             CI 模式: 仅输出新版本 CHANGELOG 内容（不修改文件）
  --from <tag>     指定起始标签（默认: 上一个版本标签）
  --to <ref>       指定结束引用（默认: HEAD）
  --output <file>  输出文件路径（默认: CHANGELOG.md）
  --dry-run        预览模式: 仅输出不修改文件
  -h, --help       显示帮助信息

示例:
  $0 0.10.0                        # 生成 v0.10.0 的 CHANGELOG
  $0 0.10.0 --from v0.9.0          # 指定起始版本
  $0 0.10.0 --ci                   # CI 模式，输出到 stdout
  $0 0.10.0 --dry-run              # 预览模式

Conventional Commits 格式:
  feat(scope): 新功能描述      → Added
  fix(scope): 修复描述         → Fixed
  perf(scope): 优化描述        → Changed
  refactor(scope): 重构描述    → Changed
  docs(scope): 文档描述        → (不计入)
  feat(scope)!: 破坏性变更     → BREAKING CHANGES
EOF
    exit 0
}

# ─── 参数解析 ────────────────────────────────────────────────
VERSION=""
CI_MODE=false
FROM_TAG=""
TO_REF="HEAD"
OUTPUT_FILE="CHANGELOG.md"
DRY_RUN=false

if [[ $# -lt 1 ]]; then
    usage
fi

VERSION="$1"
shift

while [[ $# -gt 0 ]]; do
    case "$1" in
        --ci)        CI_MODE=true; shift ;;
        --from)      FROM_TAG="$2"; shift 2 ;;
        --to)        TO_REF="$2"; shift 2 ;;
        --output)    OUTPUT_FILE="$2"; shift 2 ;;
        --dry-run)   DRY_RUN=true; shift ;;
        -h|--help)   usage ;;
        *)           error "未知参数: $1" ;;
    esac
done

# ─── 版本号校验 ──────────────────────────────────────────────
if ! echo "$VERSION" | grep -qE '^[0-9]+\.[0-9]+\.[0-9]+(-[a-zA-Z0-9.]+)?$'; then
    error "无效的版本号格式: $VERSION (期望: MAJOR.MINOR.PATCH[-prerelease])"
fi

# ─── 自动检测起始标签 ────────────────────────────────────────
if [[ -z "$FROM_TAG" ]]; then
    # 获取最近的版本标签（排除当前正在发布的版本标签）
    FROM_TAG=$(git tag --sort=-version:refname | (grep -E '^v[0-9]+\.[0-9]+\.[0-9]+$' || true) | (grep -v -E "^v?${VERSION}$" || true) | head -1)
    if [[ -z "$FROM_TAG" ]]; then
        warn "未找到已有版本标签，将从所有提交生成 CHANGELOG"
        FROM_TAG=""
    else
        info "自动检测起始标签: $FROM_TAG"
    fi
fi

# ─── 获取提交范围 ────────────────────────────────────────────
if [[ -n "$FROM_TAG" ]]; then
    COMMIT_RANGE="${FROM_TAG}..${TO_REF}"
else
    COMMIT_RANGE="$TO_REF"
fi

info "提交范围: $COMMIT_RANGE"

classify_commits() {
    local commit_range="$1"

    # 使用临时文件存储分类结果（避免子 shell 数组丢失问题）
    local tmp_dir
    tmp_dir=$(mktemp -d)
    local added_file="$tmp_dir/added"
    local fixed_file="$tmp_dir/fixed"
    local changed_file="$tmp_dir/changed"
    local breaking_file="$tmp_dir/breaking"
    local deprecated_file="$tmp_dir/deprecated"
    local removed_file="$tmp_dir/removed"
    local security_file="$tmp_dir/security"

    touch "$added_file" "$fixed_file" "$changed_file" "$breaking_file" \
          "$deprecated_file" "$removed_file" "$security_file"

    # 清理临时文件的 trap
    trap "rm -rf '$tmp_dir'" RETURN

    # 检查提交数量
    local commit_count
    if [[ -n "$FROM_TAG" ]]; then
        commit_count=$(git rev-list "$commit_range" --count 2>/dev/null || echo "0")
    else
        commit_count=$(git rev-list HEAD --count 2>/dev/null || echo "0")
    fi

    if [[ "$commit_count" -eq 0 ]]; then
        warn "提交范围内无提交记录"
        return
    fi

    info "分析 $commit_count 个提交..."

    # 逐条处理 git log 输出
    local log_cmd
    if [[ -n "$FROM_TAG" ]]; then
        log_cmd="git log $commit_range"
    else
        log_cmd="git log"
    fi

    while IFS=$'\x1f' read -r hash subject; do
        [[ -z "$hash" ]] && continue

        local short_hash="${hash:0:7}"
        local entry="- ${subject} (${short_hash})"

        # 检测破坏性变更
        if [[ "$subject" =~ (BREAKING[ -]CHANGE|\!:) ]]; then
            local breaking_desc=""
            if [[ "$subject" =~ \!:\ (.*) ]]; then
                breaking_desc="${BASH_REMATCH[1]}"
                echo "- ${breaking_desc} (${short_hash})" >> "$breaking_file"
            else
                echo "$entry" >> "$breaking_file"
            fi
        fi

        # 按 type 分类
        if [[ "$subject" =~ ^feat(\(.+\))?: ]]; then
            echo "$entry" >> "$added_file"
        elif [[ "$subject" =~ ^fix(\(.+\))?: ]]; then
            echo "$entry" >> "$fixed_file"
            if [[ "$subject" =~ (security|CVE|vulnerability|XSS|injection|CSRF) ]]; then
                echo "$entry" >> "$security_file"
            fi
        elif [[ "$subject" =~ ^perf(\(.+\))?: ]]; then
            echo "$entry" >> "$changed_file"
        elif [[ "$subject" =~ ^refactor(\(.+\))?: ]]; then
            echo "$entry" >> "$changed_file"
        elif [[ "$subject" =~ ^revert(\(.+\))?: ]]; then
            echo "$entry" >> "$fixed_file"
        elif [[ "$subject" =~ ^deprecate(\(.+\))?: ]]; then
            echo "$entry" >> "$deprecated_file"
        elif [[ "$subject" =~ ^remove(\(.+\))?: ]]; then
            echo "$entry" >> "$removed_file"
        fi
        # docs, style, test, chore, ci 不计入 CHANGELOG
    done < <($log_cmd --pretty=format:"%H%x1f%s" 2>/dev/null || true)

    # ─── 输出 CHANGELOG 内容 ────────────────────────────────
    local today
    today=$(date +%Y-%m-%d)

    # 检查是否有任何分类内容
    local has_content=false

    echo ""
    echo "## [${VERSION}] - ${today}"
    echo ""

    if [[ -s "$breaking_file" ]]; then
        has_content=true
        echo "### 💥 BREAKING CHANGES"
        echo ""
        cat "$breaking_file"
        echo ""
    fi

    if [[ -s "$added_file" ]]; then
        has_content=true
        echo "### Added"
        echo ""
        cat "$added_file"
        echo ""
    fi

    if [[ -s "$changed_file" ]]; then
        has_content=true
        echo "### Changed"
        echo ""
        cat "$changed_file"
        echo ""
    fi

    if [[ -s "$deprecated_file" ]]; then
        has_content=true
        echo "### Deprecated"
        echo ""
        cat "$deprecated_file"
        echo ""
    fi

    if [[ -s "$removed_file" ]]; then
        has_content=true
        echo "### Removed"
        echo ""
        cat "$removed_file"
        echo ""
    fi

    if [[ -s "$fixed_file" ]]; then
        has_content=true
        echo "### Fixed"
        echo ""
        cat "$fixed_file"
        echo ""
    fi

    if [[ -s "$security_file" ]]; then
        has_content=true
        echo "### Security"
        echo ""
        cat "$security_file"
        echo ""
    fi

    # 如果所有分类都为空
    if [[ "$has_content" != "true" ]]; then
        echo "### Changed"
        echo ""
        echo "- Minor updates and improvements"
        echo ""
    fi
}

# ─── 生成 CHANGELOG ──────────────────────────────────────────
generate_changelog() {
    info "正在生成 v${VERSION} 的 CHANGELOG..."

    local new_section
    new_section=$(classify_commits "$COMMIT_RANGE")

    if [[ "$CI_MODE" == "true" ]]; then
        # CI 模式：仅输出新版本内容
        echo "$new_section"
        return
    fi

    if [[ "$DRY_RUN" == "true" ]]; then
        echo "=== 预览模式 ==="
        echo "$new_section"
        echo ""
        echo "=== 不会修改 $OUTPUT_FILE ==="
        return
    fi

    # 读取现有 CHANGELOG
    local header=""
    local existing=""

    if [[ -f "$OUTPUT_FILE" ]]; then
        # 提取文件头部（前4行：标题、空行、描述、空行）
        header=$(head -6 "$OUTPUT_FILE")
        # 提取现有版本记录（跳过头部）
        existing=$(tail -n +7 "$OUTPUT_FILE")
    else
        header="# Changelog

All notable changes to SOC Copilot will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html)."
    fi

    # 组合新的 CHANGELOG
    {
        echo "$header"
        echo ""
        echo "$new_section"
        if [[ -n "$existing" ]]; then
            echo "$existing"
        fi
    } > "$OUTPUT_FILE"

    success "CHANGELOG 已更新: $OUTPUT_FILE"
}

# ─── 主流程 ──────────────────────────────────────────────────
main() {
    # 验证 git 仓库
    if ! git rev-parse --is-inside-work-tree &>/dev/null; then
        error "当前目录不是 Git 仓库"
    fi

    # 验证起始标签存在
    if [[ -n "$FROM_TAG" ]]; then
        if ! git rev-parse "$FROM_TAG" &>/dev/null; then
            error "标签 $FROM_TAG 不存在"
        fi
    fi

    generate_changelog
}

main
