#!/bin/bash
###############################################################################
# SOC Copilot Restore Script
# 恢复备份的数据
#
# 用法: ./scripts/restore.sh <backup_directory>
#
# 参数:
#   backup_directory: 备份目录路径 (例如: ./backups/20260224_120000)
###############################################################################

set -e

# 配置
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查参数
if [ -z "$1" ]; then
    log_error "Usage: $0 <backup_directory>"
    echo ""
    echo "Available backups:"
    find "$PROJECT_DIR/backups" -maxdepth 1 -type d 2>/dev/null | sort -r | head -10 || echo "  No backups found"
    exit 1
fi

BACKUP_DIR="$1"

# 检查备份目录是否存在
if [ ! -d "$BACKUP_DIR" ]; then
    log_error "Backup directory not found: $BACKUP_DIR"
    exit 1
fi

# 显示备份信息
log_info "Backup information:"
if [ -f "$BACKUP_DIR/metadata.txt" ]; then
    cat "$BACKUP_DIR/metadata.txt"
else
    log_warning "No metadata file found"
fi

echo ""
log_warning "⚠️  WARNING: This will overwrite current data!"
log_warning "The following services will be stopped during restore:"
log_warning "  - PostgreSQL"
log_warning "  - Redis"
log_warning "  - Backend"
log_warning "  - Frontend"
echo ""
read -p "Continue? (yes/no): " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    log_info "Restore cancelled"
    exit 0
fi

log_info "🔄 Starting restore from $BACKUP_DIR"
echo "======================================="

# 1. 停止服务
log_info "⏹️ Stopping services..."

cd "$PROJECT_DIR"
docker-compose -f docker-compose.prod.yml stop backend frontend 2>/dev/null || true
log_success "  Services stopped"

# 2. 恢复 PostgreSQL
log_info "📦 Restoring PostgreSQL..."

if [ -f "$BACKUP_DIR/postgres.sql.gz" ]; then
    PG_CONTAINER=$(docker ps --filter "name=soc-copilot-postgres" --format "{{.Names}}")

    if [ -z "$PG_CONTAINER" ]; then
        # 启动 PostgreSQL
        docker-compose -f docker-compose.prod.yml up -d postgres
        sleep 5
        PG_CONTAINER=$(docker ps --filter "name=soc-copilot-postgres" --format "{{.Names}}")
    fi

    # 删除现有数据库
    log_info "  Dropping existing database..."
    docker exec "$PG_CONTAINER" psql -U postgres -c "DROP DATABASE IF EXISTS soc_copilot;" || true

    # 创建新数据库
    log_info "  Creating new database..."
    docker exec "$PG_CONTAINER" psql -U postgres -c "CREATE DATABASE soc_copilot;" || true

    # 恢复数据
    log_info "  Restoring data..."
    gunzip < "$BACKUP_DIR/postgres.sql.gz" | \
        docker exec -i "$PG_CONTAINER" psql -U postgres -d soc_copilot

    log_success "  PostgreSQL restored"
else
    log_warning "  PostgreSQL backup not found, skipping..."
fi

# 3. 恢复 Redis
log_info "📦 Restoring Redis..."

if [ -f "$BACKUP_DIR/redis.rdb" ]; then
    REDIS_CONTAINER=$(docker ps --filter "name=soc-copilot-redis" --format "{{.Names}}")

    if [ -z "$REDIS_CONTAINER" ]; then
        # 启动 Redis
        docker-compose -f docker-compose.prod.yml up -d redis
        sleep 3
        REDIS_CONTAINER=$(docker ps --filter "name=soc-copilot-redis" --format "{{.Names}}")
    fi

    # 停止 Redis
    docker stop "$REDIS_CONTAINER"

    # 复制 RDB 文件
    docker cp "$BACKUP_DIR/redis.rdb" "$REDIS_CONTAINER:/data/dump.rdb"

    # 启动 Redis
    docker start "$REDIS_CONTAINER"

    sleep 3

    log_success "  Redis restored"
else
    log_warning "  Redis backup not found, skipping..."
fi

# 4. 恢复配置文件
log_info "📦 Restoring configuration files..."

if [ -f "$BACKUP_DIR/config.tar.gz" ]; then
    # 备份当前配置
    log_info "  Backing up current configuration..."
    tar czf "$PROJECT_DIR/config.backup.$(date +%Y%m%d_%H%M%S).tar.gz" \
        -C "$PROJECT_DIR" \
        docker-compose*.yml \
        backend/.env* frontend/.env* 2>/dev/null || true

    # 恢复配置
    log_info "  Extracting configuration..."
    tar xzf "$BACKUP_DIR/config.tar.gz" -C "$PROJECT_DIR"

    log_success "  Configuration restored"
    log_warning "  ⚠️  Please review restored configuration files and restart services if needed"
else
    log_warning "  Configuration backup not found, skipping..."
fi

# 5. 验证校验和
if [ -f "$BACKUP_DIR/SHA256SUMS" ]; then
    log_info "🔐 Verifying checksums..."
    cd "$BACKUP_DIR"
    if sha256sum -c SHA256SUMS; then
        log_success "  All checksums verified"
    else
        log_error "  Checksum verification failed!"
        log_warning "  Some files may be corrupted"
    fi
    cd "$PROJECT_DIR"
fi

# 6. 启动服务
log_info "▶️ Starting services..."

docker-compose -f docker-compose.prod.yml up -d

log_success "  Services started"

# 等待服务就绪
log_info "⏳ Waiting for services to be ready..."
sleep 10

# 7. 验证
log_info "🔍 Verifying restore..."

# 检查 PostgreSQL
if docker exec "$(docker ps --filter 'name=soc-copilot-postgres' --format '{{.Names}}')" \
    pg_isready -U postgres >/dev/null 2>&1; then
    log_success "  PostgreSQL is ready"
else
    log_error "  PostgreSQL is not ready"
fi

# 检查 Redis
if docker exec "$(docker ps --filter 'name=soc-copilot-redis' --format '{{.Names}}')" \
    redis-cli ping >/dev/null 2>&1; then
    log_success "  Redis is ready"
else
    log_error "  Redis is not ready"
fi

# 完成
echo "======================================="
log_success "✅ Restore completed"

# 显示服务状态
echo ""
log_info "Service status:"
docker-compose -f docker-compose.prod.yml ps

exit 0
