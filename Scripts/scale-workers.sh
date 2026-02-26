#!/bin/bash
###############################################################################
# SOC Copilot Worker Scaling Script
# 动态扩展 Alert Worker 实例数量
#
# 用法: ./scripts/scale-workers.sh [replicas]
#
# 参数:
#   replicas: Worker 实例数量 (默认: 3)
###############################################################################

set -e

# 配置
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
COMPOSE_FILE="$PROJECT_DIR/docker-compose.prod.yml"
DEFAULT_REPLICAS=3

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
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

# 获取当前 Worker 数量
get_current_replicas() {
    docker ps -a --filter "name=soc-copilot-alert-worker" --format "{{.Names}}" | wc -l | tr -d ' '
}

# 显示 Worker 状态
show_worker_status() {
    echo ""
    echo -e "${CYAN}Current Worker Status:${NC}"
    echo "┌───────────────────────────────────────────────────┐"

    docker ps -a --filter "name=soc-copilot-alert-worker" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" || echo "  No workers found"

    echo "└───────────────────────────────────────────────────┘"
    echo ""
}

# 主函数
main() {
    local replicas=${1:-$DEFAULT_REPLICAS}

    # 验证参数
    if ! [[ "$replicas" =~ ^[0-9]+$ ]]; then
        log_error "Invalid replicas count: $replicas"
        log_info "Usage: $0 [replicas]"
        exit 1
    fi

    if [ "$replicas" -lt 1 ] || [ "$replicas" -gt 10 ]; then
        log_warning "Unusual replicas count: $replicas"
        read -p "Continue anyway? (yes/no): " CONFIRM
        if [ "$CONFIRM" != "yes" ]; then
            log_info "Scaling cancelled"
            exit 0
        fi
    fi

    # 显示当前状态
    local current=$(get_current_replicas)
    echo -e "${CYAN}╔════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║${NC}      ${BLUE}SOC Copilot - Worker Scaling${NC}                   ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}      $(date '+%Y-%m-%d %H:%M:%S')                              ${CYAN}║${NC}"
    echo -e "${CYAN}╚════════════════════════════════════════════════════════╝${NC}"
    echo ""
    log_info "Current workers: $current"
    log_info "Desired workers: $replicas"

    if [ "$current" -eq "$replicas" ]; then
        log_warning "Already at $replicas workers"
        show_worker_status
        exit 0
    fi

    # 确认
    echo ""
    if [ "$replicas" -gt "$current" ]; then
        log_info "This will scale UP by $((replicas - current)) workers"
    else
        log_warning "This will scale DOWN by $((current - replicas)) workers"
    fi

    read -p "Continue? (yes/no): " CONFIRM

    if [ "$CONFIRM" != "yes" ]; then
        log_info "Scaling cancelled"
        exit 0
    fi

    # 执行扩展
    log_info "Scaling alert-worker to $replicas replicas..."

    cd "$PROJECT_DIR"

    if docker-compose -f "$COMPOSE_FILE" up -d --scale alert-worker=$replicas; then
        log_success "Scaling completed successfully"
    else
        log_error "Scaling failed"
        exit 1
    fi

    # 等待服务启动
    if [ "$replicas" -gt "$current" ]; then
        log_info "Waiting for new workers to start..."
        sleep 5
    fi

    # 显示新状态
    show_worker_status

    # 显示建议
    echo -e "${BLUE}Recommendations:${NC}"

    # 检查队列状态
    if docker ps | grep -q "soc-copilot-redis"; then
        echo ""
        log_info "Queue status:"
        docker exec "$(docker ps --filter 'name=soc-copilot-redis' --format '{{.Names}}')" \
            redis-cli XLEN alerts:critical 2>/dev/null | xargs -I {} echo "  Critical: {} messages"
        docker exec "$(docker ps --filter 'name=soc-copilot-redis' --format '{{.Names}}')" \
            redis-cli XLEN alerts:high 2>/dev/null | xargs -I {} echo "  High: {} messages"
        docker exec "$(docker ps --filter 'name=soc-copilot-redis' --format '{{.Names}}')" \
            redis-cli XLEN alerts:medium 2>/dev/null | xargs -I {} echo "  Medium: {} messages"
    fi

    log_success "✅ Worker scaling completed"
}

main "$@"
