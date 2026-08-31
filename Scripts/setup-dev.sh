#!/usr/bin/env bash
# ============================================================================
# SOC Copilot - 开发环境一键初始化脚本 (FR-004)
# ============================================================================
# 用法:
#   ./scripts/setup-dev.sh          # 完整初始化
#   ./scripts/setup-dev.sh --skip-docker  # 跳过Docker服务启动
#   ./scripts/setup-dev.sh --check-only   # 仅检查环境，不安装
# ============================================================================
set -euo pipefail

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 项目根目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# 配置
REQUIRED_PYTHON="3.12"
REQUIRED_NODE="20"
VENV_DIR="$PROJECT_ROOT/venv"
SKIP_DOCKER=false
CHECK_ONLY=false

# ============================================================================
# 工具函数
# ============================================================================

info()    { echo -e "${BLUE}[INFO]${NC}  $*"; }
success() { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error()   { echo -e "${RED}[ERROR]${NC} $*"; }

check_command() {
    if command -v "$1" &>/dev/null; then
        return 0
    else
        return 1
    fi
}

version_ge() {
    # 比较版本号: version_ge "3.12.0" "3.12" => true
    local v1="$1" v2="$2"
    # 移除前缀字母（如 v20 -> 20）
    v1="${v1#v}"
    v2="${v2#v}"
    # 简化比较：取主.次版本号比较
    local v1_major v1_minor v2_major v2_minor
    IFS='.' read -r v1_major v1_minor _ <<< "$v1"
    IFS='.' read -r v2_major v2_minor _ <<< "$v2"
    v1_major="${v1_major:-0}"; v1_minor="${v1_minor:-0}"
    v2_major="${v2_major:-0}"; v2_minor="${v2_minor:-0}"

    if [ "$v1_major" -gt "$v2_major" ]; then return 0; fi
    if [ "$v1_major" -eq "$v2_major" ] && [ "$v1_minor" -ge "$v2_minor" ]; then return 0; fi
    return 1
}

# ============================================================================
# 参数解析
# ============================================================================

for arg in "$@"; do
    case "$arg" in
        --skip-docker)  SKIP_DOCKER=true ;;
        --check-only)   CHECK_ONLY=true ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --skip-docker   Skip Docker services startup"
            echo "  --check-only    Only check environment, do not install"
            echo "  --help          Show this help message"
            exit 0
            ;;
        *)
            error "Unknown argument: $arg"
            exit 1
            ;;
    esac
done

# ============================================================================
# Step 1: 检查系统依赖
# ============================================================================

echo ""
echo "=========================================="
echo "  SOC Copilot - 开发环境初始化 (FR-004)"
echo "=========================================="
echo ""

CHECKS_PASSED=true

# 1.1 检查 Python
info "检查 Python 版本..."
if check_command python3; then
    PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    if version_ge "$PYTHON_VERSION" "$REQUIRED_PYTHON"; then
        success "Python $PYTHON_VERSION (要求 >= $REQUIRED_PYTHON)"
    else
        error "Python $PYTHON_VERSION 版本过低 (要求 >= $REQUIRED_PYTHON)"
        error "  建议使用 pyenv 安装: pyenv install $REQUIRED_PYTHON && pyenv local $REQUIRED_PYTHON"
        CHECKS_PASSED=false
    fi
else
    error "Python3 未安装"
    error "  macOS: brew install python@3.12"
    error "  或使用 pyenv: pyenv install 3.12 && pyenv local 3.12"
    CHECKS_PASSED=false
fi

# 1.2 检查 Node.js
info "检查 Node.js 版本..."
if check_command node; then
    NODE_VERSION=$(node -v | sed 's/^v//')
    NODE_VERSION_SHORT=$(echo "$NODE_VERSION" | cut -d. -f1)
    if version_ge "$NODE_VERSION_SHORT" "$REQUIRED_NODE"; then
        success "Node.js $NODE_VERSION (要求 >= $REQUIRED_NODE)"
    else
        error "Node.js $NODE_VERSION 版本过低 (要求 >= $REQUIRED_NODE)"
        error "  建议使用 nvm 安装: nvm install $REQUIRED_NODE && nvm use $REQUIRED_NODE"
        CHECKS_PASSED=false
    fi
else
    error "Node.js 未安装"
    error "  建议使用 nvm: nvm install $REQUIRED_NODE && nvm use $REQUIRED_NODE"
    CHECKS_PASSED=false
fi

# 1.3 检查 Git
info "检查 Git..."
if check_command git; then
    success "Git $(git --version | awk '{print $3}')"
else
    error "Git 未安装"
    CHECKS_PASSED=false
fi

# 1.4 检查 Docker（可选）
info "检查 Docker..."
if check_command docker; then
    if docker info &>/dev/null; then
        success "Docker 运行中"
    else
        warn "Docker 已安装但未运行，请启动 Docker Desktop"
    fi
else
    warn "Docker 未安装（可选，用于容器化开发环境）"
fi

# 1.5 检查 pip
info "检查 pip..."
if python3 -m pip --version &>/dev/null; then
    success "pip $(python3 -m pip --version | awk '{print $2}')"
else
    error "pip 未安装"
    CHECKS_PASSED=false
fi

# 1.6 检查 npm
info "检查 npm..."
if check_command npm; then
    success "npm $(npm -v)"
else
    error "npm 未安装"
    CHECKS_PASSED=false
fi

echo ""

if [ "$CHECKS_PASSED" = false ]; then
    error "环境检查未通过，请安装缺失的依赖后重新运行"
    exit 1
fi

if [ "$CHECK_ONLY" = true ]; then
    success "环境检查全部通过！"
    exit 0
fi

# ============================================================================
# Step 2: 创建 Python 虚拟环境
# ============================================================================

echo ""
info "===== 配置 Python 虚拟环境 ====="

if [ -d "$VENV_DIR" ]; then
    info "虚拟环境已存在于 $VENV_DIR"
    read -rp "是否重新创建? [y/N] " -n 1 -s RECREATE
    echo ""
    if [[ "$RECREATE" =~ ^[Yy]$ ]]; then
        info "删除旧虚拟环境..."
        rm -rf "$VENV_DIR"
        python3 -m venv "$VENV_DIR"
        success "虚拟环境已重新创建"
    else
        success "使用现有虚拟环境"
    fi
else
    info "创建 Python 虚拟环境..."
    python3 -m venv "$VENV_DIR"
    success "虚拟环境创建于 $VENV_DIR"
fi

# 激活虚拟环境
source "$VENV_DIR/bin/activate"
success "虚拟环境已激活"

# ============================================================================
# Step 3: 安装后端依赖
# ============================================================================

echo ""
info "===== 安装后端 Python 依赖 ====="

info "升级 pip..."
pip install --upgrade pip --quiet

info "安装后端生产依赖..."
cd "$PROJECT_ROOT/backend"
pip install -r requirements.txt --quiet

info "安装后端开发依赖..."
pip install -r requirements-test.txt --quiet 2>/dev/null || \
    pip install pytest pytest-asyncio pytest-cov ruff black isort mypy pre-commit --quiet

info "安装项目可编辑模式..."
pip install -e . --quiet 2>/dev/null || true

cd "$PROJECT_ROOT"
success "后端依赖安装完成"

# ============================================================================
# Step 4: 安装前端依赖
# ============================================================================

echo ""
info "===== 安装前端 Node.js 依赖 ====="

cd "$PROJECT_ROOT"

info "安装根目录依赖..."
npm ci --quiet 2>/dev/null || npm install --quiet

info "安装前端依赖..."
cd "$PROJECT_ROOT/frontend"
npm ci --quiet 2>/dev/null || npm install --quiet

cd "$PROJECT_ROOT"
success "前端依赖安装完成"

# ============================================================================
# Step 5: 安装 pre-commit hooks
# ============================================================================

echo ""
info "===== 安装 Pre-commit Hooks ====="

cd "$PROJECT_ROOT"

info "安装 pre-commit hooks..."
pre-commit install 2>/dev/null || true

info "安装 pre-push hooks (分支名验证)..."
pre-commit install --hook-type pre-push 2>/dev/null || true

info "安装 commit-msg hooks..."
pre-commit install --hook-type commit-msg 2>/dev/null || true

info "安装安全相关 hooks..."
if [ -f ".pre-commit-config-security.yaml" ]; then
    pre-commit install --config .pre-commit-config-security.yaml --hook-type pre-commit 2>/dev/null || \
        warn "安全 hooks 安装跳过（需手动配置）"
fi

success "Pre-commit hooks 安装完成"

# ============================================================================
# Step 6: 配置 .env 文件
# ============================================================================

echo ""
info "===== 配置环境变量 ====="

if [ ! -f "$PROJECT_ROOT/.env" ]; then
    if [ -f "$PROJECT_ROOT/.env.example" ]; then
        info "从 .env.example 复制 .env..."
        cp "$PROJECT_ROOT/.env.example" "$PROJECT_ROOT/.env"

        # 生成安全默认值
        GENERATED_SECRET=$(python3 -c "import secrets; print(secrets.token_urlsafe(64))" 2>/dev/null || openssl rand -base64 64)
        GENERATED_DB_PASSWORD=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))" 2>/dev/null || openssl rand -base64 32)
        GENERATED_REDIS_PASSWORD=$(python3 -c "import secrets; print(secrets.token_urlsafe(16))" 2>/dev/null || openssl rand -base64 16)

        # macOS 兼容的 sed 替换
        sed -i '' "s/^DB_PASSWORD=$/DB_PASSWORD=${GENERATED_DB_PASSWORD}/" "$PROJECT_ROOT/.env" 2>/dev/null || \
            sed -i "s/^DB_PASSWORD=$/DB_PASSWORD=${GENERATED_DB_PASSWORD}/" "$PROJECT_ROOT/.env" 2>/dev/null || true
        sed -i '' "s/^SECRET_KEY=$/SECRET_KEY=${GENERATED_SECRET}/" "$PROJECT_ROOT/.env" 2>/dev/null || \
            sed -i "s/^SECRET_KEY=$/SECRET_KEY=${GENERATED_SECRET}/" "$PROJECT_ROOT/.env" 2>/dev/null || true
        sed -i '' "s/^REDIS_PASSWORD=$/REDIS_PASSWORD=${GENERATED_REDIS_PASSWORD}/" "$PROJECT_ROOT/.env" 2>/dev/null || \
            sed -i "s/^REDIS_PASSWORD=$/REDIS_PASSWORD=${GENERATED_REDIS_PASSWORD}/" "$PROJECT_ROOT/.env" 2>/dev/null || true

        success ".env 文件已创建（含自动生成的密钥）"
    else
        warn ".env.example 不存在，请手动创建 .env 文件"
    fi
else
    success ".env 文件已存在"
fi

# ============================================================================
# Step 7: 启动 Docker 服务（可选）
# ============================================================================

if [ "$SKIP_DOCKER" = false ]; then
    echo ""
    info "===== 启动 Docker 开发服务 ====="

    if check_command docker && docker info &>/dev/null; then
        info "启动 PostgreSQL 和 Redis..."
        cd "$PROJECT_ROOT"
        docker compose up -d postgres redis 2>/dev/null || \
            docker-compose up -d postgres redis 2>/dev/null || \
            warn "Docker 服务启动失败，请手动启动"

        # 等待服务就绪
        info "等待服务就绪..."
        sleep 5

        if docker compose exec postgres pg_isready &>/dev/null 2>&1 || \
           docker-compose exec postgres pg_isready &>/dev/null 2>&1; then
            success "PostgreSQL 服务就绪"
        else
            warn "PostgreSQL 服务可能尚未就绪，请检查: docker compose ps"
        fi

        if docker compose exec redis redis-cli ping &>/dev/null 2>&1 || \
           docker-compose exec redis redis-cli ping &>/dev/null 2>&1; then
            success "Redis 服务就绪"
        else
            warn "Redis 服务可能尚未就绪，请检查: docker compose ps"
        fi
    else
        warn "Docker 不可用，跳过服务启动"
        info "请确保 PostgreSQL 和 Redis 可用，或手动启动 Docker 服务"
    fi
else
    echo ""
    info "跳过 Docker 服务启动 (--skip-docker)"
fi

# ============================================================================
# Step 8: 运行数据库迁移
# ============================================================================

echo ""
info "===== 运行数据库迁移 ====="

cd "$PROJECT_ROOT/backend"
if [ -d "migrations_alembic" ]; then
    info "运行 Alembic 迁移..."
    source "$VENV_DIR/bin/activate"
    alembic upgrade head 2>/dev/null && \
        success "数据库迁移完成" || \
        warn "数据库迁移失败，请检查数据库连接配置"
else
    warn "未找到 Alembic 迁移目录，跳过数据库迁移"
fi

cd "$PROJECT_ROOT"

# ============================================================================
# Step 9: 验证环境
# ============================================================================

echo ""
info "===== 验证开发环境 ====="

VERIFY_PASSED=true

# 验证虚拟环境
if [ -d "$VENV_DIR" ]; then
    success "Python 虚拟环境: $VENV_DIR"
else
    error "Python 虚拟环境缺失"
    VERIFY_PASSED=false
fi

# 验证后端依赖
source "$VENV_DIR/bin/activate"
if python3 -c "import fastapi" 2>/dev/null; then
    success "后端核心依赖: OK"
else
    error "后端核心依赖缺失"
    VERIFY_PASSED=false
fi

# 验证前端依赖
if [ -d "$PROJECT_ROOT/frontend/node_modules" ]; then
    success "前端依赖: OK"
else
    error "前端依赖缺失"
    VERIFY_PASSED=false
fi

# 验证 pre-commit
if [ -f "$PROJECT_ROOT/.git/hooks/pre-commit" ]; then
    success "Pre-commit hooks: 已安装"
else
    warn "Pre-commit hooks: 未安装（运行: pre-commit install）"
fi

# 验证 .env
if [ -f "$PROJECT_ROOT/.env" ]; then
    success "环境变量文件: .env"
else
    warn "环境变量文件: 缺失（运行: cp .env.example .env）"
fi

echo ""
echo "=========================================="
if [ "$VERIFY_PASSED" = true ]; then
    success "🎉 开发环境初始化完成！"
else
    warn "⚠️  开发环境初始化部分完成，请检查上述错误"
fi
echo "=========================================="
echo ""
echo "快速开始:"
echo "  make dev           # 启动前后端开发服务器"
echo "  make dev-backend   # 仅启动后端 (port 8000)"
echo "  make dev-frontend  # 仅启动前端 (port 3003)"
echo "  make lint          # 运行代码检查"
echo "  make test          # 运行测试"
echo "  make help          # 查看所有可用命令"
echo ""
echo "文档:"
echo "  docs/dev-environment.md  # 开发环境详细文档"
echo "  DEVELOPMENT_GUIDE.md     # 开发指南"
echo ""
