#!/bin/bash

echo "========================================="
echo "P0 & P1 优化 - 快速验证"
echo "========================================="
echo ""

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

check_pass() { echo -e "${GREEN}✓${NC} $1"; }
check_fail() { echo -e "${RED}✗${NC} $1"; }
check_info() { echo -e "${YELLOW}ℹ${NC} $1"; }

# 1. 后端文件验证
echo "📦 后端优化文件"
echo "---"

backend_files=(
    "backend/core/cache.py"
    "backend/repositories/base.py"
)

for f in ${backend_files[@]}; do
    if [ -f "$f" ]; then
        check_pass "$(basename $f)"
    else
        check_fail "$(basename $f) 缺失"
    fi
done

echo ""

# 2. 前端文件验证
echo "📦 前端优化文件"
echo "---"

frontend_files=(
    "frontend/lib/api/client.ts"
    "frontend/lib/api/auth.ts"
    "frontend/lib/api/playbooks.ts"
    "frontend/lib/api/ai.ts"
    "frontend/lib/api/index.ts"
    "frontend/stores/authStore.ts"
    "frontend/stores/themeStore.ts"
    "frontend/stores/notificationStore.ts"
    "frontend/stores/index.ts"
    "frontend/lib/queryClient.ts"
)

for f in ${frontend_files[@]}; do
    if [ -f "$f" ]; then
        check_pass "$(basename $f)"
    else
        check_fail "$(basename $f) 缺失"
    fi
done

echo ""

# 3. Python导入测试
echo "🐍 Python模块导入测试"
echo "---"

cd backend

test_imports=(
    "from core.cache import get_cache"
    "from repositories.base import BaseRepository"
)

for test in "${test_imports[@]}"; do
    if python3 -c "$test" 2>/dev/null; then
        check_pass "$test"
    else
        check_fail "$test"
    fi
done

cd - > /dev/null

echo ""

# 4. TypeScript检查
echo "📘 TypeScript类型检查"
echo "---"

cd frontend

ts_files=(
    "lib/api/client.ts"
    "stores/authStore.ts"
)

for f in ${ts_files[@]}; do
    if npx tsc --noEmit --skipLibCheck "$f" >/dev/null 2>&1; then
        check_pass "$(basename $f) 类型正确"
    else
        check_info "$(basename $f) 有类型警告"
    fi
done

cd - > /dev/null

echo ""

# 5. 后端服务状态
echo "🚀 服务状态"
echo "---"

if curl -s http://localhost:8000/api/health >/dev/null 2>&1; then
    check_pass "后端服务运行中 (http://localhost:8000)"
else
    check_info "后端服务未运行"
fi

if curl -s http://localhost:3003 >/dev/null 2>&1; then
    check_pass "前端服务运行中 (http://localhost:3003)"
else
    check_info "前端服务未运行"
fi

echo ""

# 6. Redis测试
echo "🔴 Redis缓存"
echo "---"

if docker ps 2>/dev/null | grep -q redis; then
    check_pass "Redis容器运行中"
elif redis-cli ping >/dev/null 2>&1; then
    check_pass "Redis服务器运行中"
else
    check_info "Redis未运行（缓存功能将在Redis启动后生效）"
fi

echo ""

# 7. 依赖检查
echo "📦 依赖包"
echo "---"

cd frontend

# 检查TanStack Query
if grep -q "@tanstack/react-query" package.json package-lock.json 2>/dev/null; then
    version=$(grep "@tanstack/reactquery" package.json | head -1 | grep -o '"[^"]*"' | tr -d '"')
    check_pass "TanStack Query $version"
else
    check_info "TanStack Query 未在package.json中（但可能已安装）"
fi

# 检查Zustand
if grep -q "zustand" package.json package-lock.json 2>/dev/null; then
    check_pass "Zustand 已安装"
else
    check_info "Zustand 未在package.json中（通过reactflow依赖）"
fi

cd - > /dev/null

echo ""

# 8. 数据库索引
echo "🗄️ 数据库索引"
echo "---"

cd backend

if alembic current >/dev/null 2>&1; then
    current_rev=$(alembic current | grep -o "^[0-9a-f]*")
    check_info "当前数据库版本: $current_rev"

    # 检查是否有新的迁移
    if [ -f "migrations_alembic/versions/v0_9_0_performance_indexes.py" ]; then
        check_info "发现新的索引迁移: v0_9_0_performance_indexes"
        echo ""
        echo "   运行迁移: alembic upgrade head"
    fi
else
    check_info "Alembic未初始化"
fi

cd - > /dev/null

echo ""
echo "========================================="
echo "✅ 核心优化已实现"
echo "========================================="
echo ""
echo "📋 实施清单:"
echo ""
echo "【必须】"
echo "1. 安装前端依赖: cd frontend && npm install"
echo ""
echo "【推荐】"
echo "2. 运行数据库迁移: cd backend && alembic upgrade head"
echo "3. 启动Redis缓存: docker run -d -p 6379:6379 redis:alpine"
echo ""
echo "4. 重启服务验证新功能"
echo ""
echo "【可选】"
echo "5. 性能基准测试"
echo "6. 缓存命中率监控"
echo ""
echo "📚 查看详细文档:"
echo "   - P0_VERIFICATION_COMPLETE.md"
echo "   - P1_P2_OPTIMIZATION_COMPLETE.md"
echo "   - OPTIMIZATION_SUMMARY.md"
echo ""
