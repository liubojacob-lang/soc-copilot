#!/bin/bash
###############################################################################
# SOC Copilot Queue Monitoring Script
# 监控 Redis Streams 队列状态
#
# 用法: ./scripts/monitor-queues.sh
###############################################################################

set -e

# 配置
REDIS_CONTAINER="${REDIS_CONTAINER:-soc-copilot-redis-prod}"
REFRESH_INTERVAL=${REFRESH_INTERVAL:-5}

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 清屏并显示标题
show_header() {
    clear
    echo -e "${CYAN}╔════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║${NC}      ${BLUE}SOC Copilot - Queue Monitor${NC}                 ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}      $(date '+%Y-%m-%d %H:%M:%S')                              ${CYAN}║${NC}"
    echo -e "${CYAN}╚════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

# 获取队列长度
get_queue_length() {
    local stream=$1
    docker exec "$REDIS_CONTAINER" redis-cli XLEN "$stream" 2>/dev/null || echo "0"
}

# 获取待处理消息数
get_pending_count() {
    local stream=$1
    docker exec "$REDIS_CONTAINER" redis-cli XPENDING "$stream" "soc_workers" "- + " "10" 2>/dev/null | grep -c "^[0-9]" || echo "0"
}

# 显示队列统计
show_queue_stats() {
    echo -e "${BLUE}Queue Statistics:${NC}"
    echo "┌────────────┬──────────┬─────────┬────────────┐"
    echo "│ Severity   │ Length   │ Pending │ Status     │"
    echo "├────────────┼──────────┼─────────┼────────────┤"

    for severity in critical high medium low; do
        stream="alerts:$severity"
        length=$(get_queue_length "$stream")
        pending=$(get_pending_count "$stream")

        # 确定状态
        if [ "$length" -eq 0 ]; then
            status="${GREEN}Idle${NC}"
        elif [ "$length" -lt 100 ]; then
            status="${GREEN}Normal${NC}"
        elif [ "$length" -lt 500 ]; then
            status="${YELLOW}Busy${NC}"
        else
            status="${RED}Overload${NC}"
        fi

        # 格式化输出
        printf "│ %-10s │ %-8s │ %-7s │ " "$severity" "$length" "$pending"
        echo -e "$status       │"
    done

    echo "└────────────┴──────────┴─────────┴────────────┘"
    echo ""
}

# 显示消费者组信息
show_consumer_info() {
    echo -e "${BLUE}Consumer Groups:${NC}"
    echo "┌────────────────────────────────────────────────┐"

    for severity in critical high medium low; do
        stream="alerts:$severity"
        info=$(docker exec "$REDIS_CONTAINER" redis-cli XINFO GROUPS "$stream" 2>/dev/null || echo "")

        if [ -n "$info" ]; then
            name=$(echo "$info" | grep "name" | awk '{print $2}')
            consumers=$(echo "$info" | grep "consumers" | awk '{print $2}')
            pending=$(echo "$info" | grep "pending" | awk '{print $2}')
            printf "│ %-10s: Group=%s, Consumers=%s, Pending=%s │\n" \
                "$severity" "$name" "$consumers" "$pending"
        fi
    done

    echo "└────────────────────────────────────────────────┘"
    echo ""
}

# 显示 Redis 信息
show_redis_info() {
    echo -e "${BLUE}Redis Information:${NC}"
    local memory=$(docker exec "$REDIS_CONTAINER" redis-cli INFO memory | grep used_memory_human | cut -d: -f2 | tr -d '\r')
    local connections=$(docker exec "$REDIS_CONTAINER" redis-cli INFO clients | grep connected_clients | cut -d: -f2 | tr -d '\r')
    local uptime=$(docker exec "$REDIS_CONTAINER" redis-cli INFO server | grep uptime_in_days | cut -d: -f2 | tr -d '\r')

    echo "┌────────────────────────────────────────────────┐"
    printf "│ Memory Used: %-30s │\n" "$memory"
    printf "│ Connections: %-30s │\n" "$connections"
    printf "│ Uptime: %-34s │\n" "$uptime days"
    echo "└────────────────────────────────────────────────┘"
    echo ""
}

# 显示建议
show_recommendations() {
    echo -e "${BLUE}Recommendations:${NC}"

    for severity in critical high medium low; do
        stream="alerts:$severity"
        length=$(get_queue_length "$stream")

        if [ "$length" -gt 500 ]; then
            echo -e "  ${RED}⚠${NC} $severity queue is overloaded ($length messages)"
            echo -e "     Consider scaling up alert-worker instances"
        elif [ "$length" -gt 100 ]; then
            echo -e "  ${YELLOW}⚡${NC} $severity queue is busy ($length messages)"
        fi
    done

    echo ""
    echo -e "Press ${CYAN}Ctrl+C${NC} to exit, ${CYAN}r${NC} to force refresh, or wait $REFRESH_INTERVAL seconds..."
}

# 主循环
main() {
    # 检查 Redis 是否运行
    if ! docker ps | grep -q "$REDIS_CONTAINER"; then
        echo -e "${RED}Error: Redis container not found: $REDIS_CONTAINER${NC}"
        exit 1
    fi

    trap 'echo -e "\n${YELLOW}Monitoring stopped${NC}"; exit 0' INT

    while true; do
        show_header
        show_queue_stats
        show_consumer_info
        show_redis_info
        show_recommendations

        # 等待用户输入或超时
        read -t "$REFRESH_INTERVAL" -n 1 input 2>/dev/null || true

        if [ "$input" = "r" ]; then
            continue
        fi
    done
}

main "$@"
