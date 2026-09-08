#!/usr/bin/env bash
# ==============================================================================
# SOC Copilot - Local Development Health & Resource Doctor
# 快速排查本地开发服务负载、风扇狂转、内存泄漏与僵尸进程
# ==============================================================================

GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${CYAN}======================================================${NC}"
echo -e "${CYAN}   SOC Copilot - Local Dev Resource Doctor   ${NC}"
echo -e "${CYAN}======================================================${NC}"

# 1. 检查整体系统负载
echo -e "\n${GREEN}[1/4] 当前系统整体负载:${NC}"
uptime

# 2. 检查监听端口 (3000, 3003, 8000)
echo -e "\n${GREEN}[2/4] 本地开发服务端口监听状态:${NC}"
for PORT in 3000 3003 8000; do
  PID=$(lsof -ti :$PORT -sTCP:LISTEN 2>/dev/null | head -n 1 || true)
  if [ -n "$PID" ]; then
    CMD=$(ps -p $PID -o args= 2>/dev/null || true)
    CPU=$(ps -p $PID -o %cpu= 2>/dev/null | tr -d ' ' || true)
    MEM=$(ps -p $PID -o %mem= 2>/dev/null | tr -d ' ' || true)
    TIME=$(ps -p $PID -o etime= 2>/dev/null | tr -d ' ' || true)
    echo -e "  • 端口 :${PORT} ➔ PID ${YELLOW}${PID}${NC} | CPU: ${YELLOW}${CPU}%${NC} | MEM: ${YELLOW}${MEM}%${NC} | 运行: ${TIME}"
    echo -e "    命令: ${CMD:0:70}..."
  else
    echo -e "  • 端口 :${PORT} ➔ 空闲 (未启动)"
  fi
done

# 3. 检查高 CPU/高内存占用异常进程
echo -e "\n${GREEN}[3/4] 检测工程相关的异常高耗能进程:${NC}"
FOUND_HOG=0
while read -r user pid cpu mem etime cmd; do
  if [ -n "$pid" ] && [ "$pid" != "PID" ]; then
    is_high=$(awk -v c="$cpu" -v m="$mem" 'BEGIN { if (c > 100.0 || m > 8.0) print 1; else print 0 }')
    if [ "$is_high" -eq 1 ]; then
      echo -e "  ${RED}⚠️ 发现高负载进程:${NC} PID $pid | CPU: ${cpu}% | MEM: ${mem}% | 耗时: $etime"
      echo -e "     指令: $cmd"
      FOUND_HOG=1
    fi
  fi
done < <(ps -A -o user,pid,%cpu,%mem,etime,command | grep -E "next-server|node.*next|python.*main" | grep -v "grep" | head -n 10)

if [ "$FOUND_HOG" -eq 0 ]; then
  echo -e "  ${GREEN}✓ 未发现工程相关的 CPU 飙高或内存泄漏进程${NC}"
fi

# 4. 操作选项：若传入 --clean 则自动清理缓存并释放卡死进程
if [ "$1" == "--clean" ] || [ "$1" == "-c" ]; then
  echo -e "\n${YELLOW}[4/4] 执行一键清理与缓存释放...${NC}"
  for PORT in 3003 3000; do
    PIDS=$(lsof -ti :$PORT -sTCP:LISTEN 2>/dev/null | head -n 1 || true)
    if [ -n "$PIDS" ]; then
      echo -e "  ➔ 正在关闭端口 :$PORT 上的进程 (PID: $PIDS)..."
      kill -9 $PIDS 2>/dev/null || true
    fi
  done
  if [ -d "frontend/.next" ]; then
    echo -e "  ➔ 清理 frontend/.next 编译缓存..."
    rm -rf frontend/.next
  fi
  echo -e "  ${GREEN}✓ 清理完成！${NC}"
else
  echo -e "\n${GREEN}[4/4] 快速健康建议:${NC}"
  echo -e "  • 如需一键终止并清理 Next 缓存，可执行: ${CYAN}./scripts/dev-doctor.sh --clean${NC}"
  echo -e "  • 推荐使用低功耗 Rust 引擎启动前端:   ${CYAN}cd frontend && npm run dev:turbo${NC}"
fi

echo -e "\n${CYAN}======================================================${NC}\n"
