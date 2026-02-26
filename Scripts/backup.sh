#!/bin/bash
###############################################################################
# SOC Copilot Backup Script
# 自动备份 PostgreSQL、Redis、配置文件
#
# 用法: ./scripts/backup.sh [dry-run]
#
# 环境变量:
#   BACKUP_DIR: 备份目录 (默认: ./backups)
#   BACKUP_RETENTION_DAYS: 保留天数 (默认: 30)
###############################################################################

set -e

# 配置
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
BACKUP_DIR="${BACKUP_DIR:-$PROJECT_DIR/backups}"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-30}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_PATH="$BACKUP_DIR/$TIMESTAMP"

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

# 检查 dry-run 模式
DRY_RUN=false
if [ "$1" == "dry-run" ]; then
    DRY_RUN=true
    log_warning "Dry-run mode: no actual backups will be created"
fi

# 创建备份目录
log_info "Creating backup directory: $BACKUP_PATH"
if [ "$DRY_RUN" = false ]; then
    mkdir -p "$BACKUP_PATH"
fi

log_info "🔄 Starting SOC Copilot backup at $(date)"
echo "======================================="

# 1. PostgreSQL 备份
log_info "📦 Backing up PostgreSQL..."

if docker ps | grep -q "soc-copilot-postgres"; then
    PG_CONTAINER=$(docker ps --filter "name=soc-copilot-postgres" --format "{{.Names}}")

    if [ "$DRY_RUN" = false ]; then
        docker exec "$PG_CONTAINER" pg_dump -U postgres soc_copilot | \
            gzip > "$BACKUP_PATH/postgres.sql.gz"

        PG_SIZE=$(du -h "$BACKUP_PATH/postgres.sql.gz" | cut -f1)
        log_success "  PostgreSQL backup completed: $PG_SIZE"
    else
        log_info "  [DRY-RUN] Would backup PostgreSQL"
    fi
else
    log_warning "  PostgreSQL container not found, skipping..."
fi

# 2. Redis 备份
log_info "📦 Backing up Redis..."

if docker ps | grep -q "soc-copilot-redis"; then
    REDIS_CONTAINER=$(docker ps --filter "name=soc-copilot-redis" --format "{{.Names}}")

    if [ "$DRY_RUN" = false ]; then
        # 创建 RDB 快照
        docker exec "$REDIS_CONTAINER" redis-cli BGSAVE

        # 等待快照完成
        sleep 2

        # 复制 RDB 文件
        docker cp "$REDIS_CONTAINER:/data/dump.rdb" "$BACKUP_PATH/redis.rdb"

        REDIS_SIZE=$(du -h "$BACKUP_PATH/redis.rdb" | cut -f1)
        log_success "  Redis backup completed: $REDIS_SIZE"
    else
        log_info "  [DRY-RUN] Would backup Redis"
    fi
else
    log_warning "  Redis container not found, skipping..."
fi

# 3. 配置文件备份
log_info "📦 Backing up configuration files..."

if [ "$DRY_RUN" = false ]; then
    # 备份环境变量文件
    for env_file in .env .env.local .env.production backend/.env frontend/.env.local; do
        if [ -f "$PROJECT_DIR/$env_file" ]; then
            cp "$PROJECT_DIR/$env_file" "$BACKUP_PATH/env_$(basename $env_file)"
        fi
    done

    # 备份 Docker Compose 文件
    cp "$PROJECT_DIR"/docker-compose*.yml "$BACKUP_PATH/" 2>/dev/null || true

    # 打包配置
    tar czf "$BACKUP_PATH/config.tar.gz" -C "$PROJECT_DIR" \
        docker-compose*.yml \
        backend/.env* frontend/.env* 2>/dev/null || true

    CONFIG_SIZE=$(du -h "$BACKUP_PATH/config.tar.gz" | cut -f1)
    log_success "  Configuration backup completed: $CONFIG_SIZE"
else
    log_info "  [DRY-RUN] Would backup configuration files"
fi

# 4. 数据库迁移文件备份
log_info "📦 Backing up database migrations..."

if [ "$DRY_RUN" = false ]; then
    if [ -d "$PROJECT_DIR/backend/alembic" ]; then
        cp -r "$PROJECT_DIR/backend/alembic" "$BACKUP_PATH/alembic"
        log_success "  Migrations backup completed"
    fi
else
    log_info "  [DRY-RUN] Would backup migrations"
fi

# 5. 写入备份元数据
log_info "📝 Writing backup metadata..."

if [ "$DRY_RUN" = false ]; then
    cat > "$BACKUP_PATH/metadata.txt" << EOF
SOC Copilot Backup Metadata
==========================
Backup Date: $(date)
Backup Version: v0.8.0
Hostname: $(hostname)

Backup Components:
- PostgreSQL: ${PG_SIZE:-N/A}
- Redis: ${REDIS_SIZE:-N/A}
- Configuration: ${CONFIG_SIZE:-N/A}

Files:
$(ls -lh "$BACKUP_PATH" | tail -n +2 | awk '{print "  " $9 " (" $5 ")"}')

System Info:
- OS: $(uname -s)
- Kernel: $(uname -r)
- Docker: $(docker --version)
EOF

    log_success "  Metadata written"
fi

# 6. 计算校验和
log_info "🔐 Calculating checksums..."

if [ "$DRY_RUN" = false ]; then
    cd "$BACKUP_PATH"
    sha256sum *.{gz,rdb,sql} 2>/dev/null > SHA256SUMS || true
    cd "$PROJECT_DIR"
    log_success "  Checksums calculated"
fi

# 7. 清理旧备份
log_info "🧹 Cleaning old backups (retention: $RETENTION_DAYS days)..."

if [ "$DRY_RUN" = false ]; then
    OLD_BACKUPS=$(find "$BACKUP_DIR" -maxdepth 1 -type d -mtime +$RETENTION_DAYS 2>/dev/null || true)

    if [ -n "$OLD_BACKUPS" ]; then
        echo "$OLD_BACKUPS" | while read old_backup; do
            log_info "  Removing old backup: $old_backup"
            rm -rf "$old_backup"
        done
        log_success "  Old backups cleaned"
    else
        log_info "  No old backups to clean"
    fi
else
    log_info "  [DRY-RUN] Would clean backups older than $RETENTION_DAYS days"
fi

# 完成
echo "======================================="
log_success "✅ Backup completed: $BACKUP_PATH"

# 列出备份内容
if [ "$DRY_RUN" = false ]; then
    echo ""
    log_info "Backup contents:"
    ls -lh "$BACKUP_PATH" | tail -n +2

    # 计算总大小
    TOTAL_SIZE=$(du -sh "$BACKUP_PATH" | cut -f1)
    log_info "Total backup size: $TOTAL_SIZE"
fi

exit 0
