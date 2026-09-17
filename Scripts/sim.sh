#!/usr/bin/env bash
# ==============================================================================
# SOC Copilot 本地独立仿真环境控制与极速更新脚本
# 用法:
#   ./Scripts/sim.sh [命令] [参数]
# ==============================================================================

set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
COMPOSE_FILE="$ROOT_DIR/docker-compose.local-sim.yml"
COMPOSE_DEV_FILE="$ROOT_DIR/docker-compose.local-sim.dev.yml"

# ======================== 仿真环境变量注入 ========================
# composer 文件里的敏感值全部写成 ${VAR:?} 强制注入、不再带默认值
# （此前用 ":-默认值" 会把真实密钥提交进 git 历史）。
# 这里把 .env.local-sim（优先）或 .env 通过 --env-file 交给 compose 做插值，
# 不用 source，避免密码里的 # / ! 被 shell 解析破坏。
SIM_ENV_FILE="$ROOT_DIR/.env.local-sim"
if [ ! -f "$SIM_ENV_FILE" ]; then
    SIM_ENV_FILE="$ROOT_DIR/.env"
fi

# 统一入口：所有 docker compose 调用都走这里，确保带上 env 文件。
# 只有真正要起服务/构建的动作才做变量预检 —— stop / logs / ps 等即使
# 变量缺失也必须能执行，否则环境一旦配置不全就停不下来。
compose_sim() {
    case " $* " in
        *" up "* | *" build "* | *" restart "* | *" start "* | *" run "*)
            check_sim_env || return 1
            ;;
    esac
    docker compose -f "$COMPOSE_FILE" --env-file "$SIM_ENV_FILE" "$@"
}

# 预检：缺失的必需变量直接给出可执行的补救提示，而不是让 compose 抛一句
# "required variable is missing" 就退出
REQUIRED_SIM_VARS=(
    SIM_DB_PASSWORD
    SIM_REDIS_PASSWORD
    JWT_SECRET
    SECRET_ENCRYPTION_KEY
    BOOTSTRAP_ADMIN_PASSWORD
    ZHIPU_API_KEY
    NVIDIA_API_KEY
)

check_sim_env() {
    local missing=()
    local key

    if [ ! -f "$SIM_ENV_FILE" ]; then
        error "未找到环境变量文件：$SIM_ENV_FILE"
        info  "请复制模板后填入真实值：cp .env.local-sim.example .env.local-sim"
        return 1
    fi

    for key in "${REQUIRED_SIM_VARS[@]}"; do
        # 只看键是否存在，不打印值
        if ! grep -qE "^[[:space:]]*${key}=." "$SIM_ENV_FILE"; then
            missing+=("$key")
        fi
    done

    if [ ${#missing[@]} -gt 0 ]; then
        error "仿真环境缺少必需变量，已停止（不会使用任何内置默认值）"
        for key in "${missing[@]}"; do
            echo -e "  ${YELLOW}缺${NC} $key"
        done
        info "请补进 $SIM_ENV_FILE，模板见 .env.local-sim.example"
        info "生成密钥：openssl rand -hex 32（JWT_SECRET）"
        info "生成 Fernet 键：python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
        return 1
    fi

    return 0
}

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

info() {
    echo -e "${CYAN}[INFO]${NC} $1"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查 Docker 运行环境
check_docker() {
    if ! command -v docker &> /dev/null; then
        error "未检测到 Docker，请先安装并启动 Docker Desktop。"
        exit 1
    fi
    if ! docker info &> /dev/null; then
        error "Docker 守护进程未运行，请先启动 Docker。"
        exit 1
    fi
}

# 帮助说明
show_help() {
    echo -e "${BOLD}${CYAN}SOC Copilot 仿真环境运维管理工具${NC}"
    echo -e "=================================================="
    echo -e "${BOLD}基础服务管理:${NC}"
    echo -e "  ${GREEN}./Scripts/sim.sh status${NC}           查看仿真环境所有容器的运行状态与端口"
    echo -e "  ${GREEN}./Scripts/sim.sh start${NC}            启动标准仿真环境 (生产镜像模式)"
    echo -e "  ${GREEN}./Scripts/sim.sh stop${NC}             停止仿真环境容器"
    echo -e "  ${GREEN}./Scripts/sim.sh restart${NC}          重启仿真环境服务"
    echo -e "  ${GREEN}./Scripts/sim.sh logs [服务名]${NC}     实时查看日志 (frontend / backend / postgres / redis)"
    echo ""
    echo -e "${BOLD}高效热重载与同步 (推荐日常调试):${NC}"
    echo -e "  ${GREEN}./Scripts/sim.sh dev${NC}              一键启动【热重载模式】(后端挂载宿主机源码，保存即生效)"
    echo -e "  ${GREEN}./Scripts/sim.sh watch${NC}            启动【前端文件自动监听同步守护】(文件一保存，全自动同步仿真前端)"
    echo -e "  ${GREEN}./Scripts/sim.sh update [组件]${NC}     极速更新 (利用宿主机增量缓存注入，仅需数秒)"
    echo -e "                                    - ${YELLOW}update frontend${NC} (仅秒级同步前端)"
    echo -e "                                    - ${YELLOW}update backend${NC}  (仅快速重启后端)"
    echo -e "                                    - ${YELLOW}update all${NC}      (同步前端 + 后端)"
    echo -e "  ${GREEN}./Scripts/sim.sh sync-data${NC}        将本地开发 SQLite 数据同步至仿真 Postgres"
    echo ""
    echo -e "${BOLD}完整镜像构建 (用于正式发版前全量验证):${NC}"
    echo -e "  ${GREEN}./Scripts/sim.sh build [组件]${NC}      全量重新构建 Docker 镜像 (带 BuildKit 缓存加速)"
    echo -e "=================================================="
}

# 查看服务状态
cmd_status() {
    check_docker
    echo -e "\n${BOLD}=== SOC Copilot 仿真环境状态 ===${NC}"
    docker ps --filter "name=soc-.*-sim" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
    echo ""
    echo -e "${BOLD}服务访问入口:${NC}"
    echo -e "  • 前端界面:   ${CYAN}http://127.0.0.1:13000${NC} (映射至容器 3000)"
    echo -e "  • 后端接口:   ${CYAN}http://127.0.0.1:18088${NC} (映射至容器 8000)"
    echo -e "  • 数据库:     ${CYAN}127.0.0.1:15432${NC}       (PostgreSQL 15)"
    echo -e "  • 缓存:       ${CYAN}127.0.0.1:16379${NC}       (Redis 7)"
    echo ""
}

# 启动仿真环境（生产模式）
cmd_start() {
    check_docker
    info "正在启动 SOC Copilot 仿真环境 (标准生产模式)..."
    cd "$ROOT_DIR"
    compose_sim up -d --remove-orphans
    cmd_status
    success "仿真环境已成功启动！"
}

# 启动热重载开发模式
cmd_dev() {
    check_docker
    info "正在以【全栈热重载挂载模式】启动仿真环境..."
    info "提示: 前端 (Next.js Fast Refresh) 与后端 (FastAPI uvicorn --reload) 均已直接挂载宿主机源码，保存文件即秒级生效！"
    cd "$ROOT_DIR"
    compose_sim -f "$COMPOSE_DEV_FILE" up -d --remove-orphans
    cmd_status
    success "全栈热重载仿真环境已就绪！"
}

# 停止服务
cmd_stop() {
    check_docker
    info "正在停止仿真环境容器..."
    cd "$ROOT_DIR"
    compose_sim stop
    success "仿真容器已停止。"
}

# 重启服务
cmd_restart() {
    check_docker
    info "正在重启仿真环境容器..."
    cd "$ROOT_DIR"
    compose_sim restart
    success "重启完成。"
    cmd_status
}

# 数据库状态检查与同步
cmd_sync_data() {
    if [ ! -f "$ROOT_DIR/data/app.db" ]; then
        success "开发库已完全退休，开发环境与仿真环境已 100% 统一直连仿真 PostgreSQL (15432 端口)，数据实时一致，无需手动同步！"
        return 0
    fi
    info "检测到历史 SQLite 开发库，开始将数据迁移同步至仿真 PostgreSQL..."
    cd "$ROOT_DIR"
    python3 "$ROOT_DIR/Scripts/sync_dev_to_sim.py"
    success "数据同步完成！"
}

# 极速增量更新前端 (宿主机增量编译 + 容器热注入，无需耗时几分钟全量打包)
fast_update_frontend() {
    info "正在利用宿主机快速增量构建前端静态产物..."
    cd "$ROOT_DIR/frontend"
    # Next 的 rewrites 在构建期固化进 routes-manifest.json，运行时 compose 的
    # NEXT_PUBLIC_API_URL 覆盖不了它。frontend/.env.local 里是宿主机开发用的
    # 127.0.0.1:8088，直接构建会把容器内所有 /api 代理指向一个不存在的端口
    # (ECONNREFUSED)，整个仿真前端会变成"页面在但点哪都没反应"。
    # 显式覆盖为容器网络内的服务名，与 frontend/Dockerfile 的构建保持一致。
    # 另外 webpack 文件系统缓存把 node_modules 视为按包版本管理，patch-next.mjs
    # 直接改动 next 源码不会让缓存失效，必须清缓存，否则产物仍是未打补丁的旧 chunk。
    rm -rf .next/cache
    NEXT_PUBLIC_API_URL=http://backend:8000 npm run build

    # 定位真正包含 server.js 的 standalone 应用根：next.config.js 的
    # outputFileTracingRoot 指向仓库根时，产物会嵌套为 standalone/frontend/，
    # 整包 cp standalone/. 会把应用放到 /app/frontend/ 下且填不回 .next，容器必挂。
    local standalone_dir app_src nested_server_js
    standalone_dir="$ROOT_DIR/frontend/.next/standalone"
    app_src="$standalone_dir"
    if [ ! -f "$standalone_dir/server.js" ]; then
        nested_server_js="$(find "$standalone_dir" -mindepth 2 -maxdepth 4 -name server.js -not -path "*/node_modules/*" -print -quit 2>/dev/null || true)"
        [ -n "$nested_server_js" ] && app_src="$(dirname "$nested_server_js")"
    fi
    if [ ! -f "$app_src/server.js" ]; then
        error "未在 $standalone_dir 下找到 server.js，前端构建产物异常，中止注入。"
        return 1
    fi

    info "正在将构建产物热注入容器 soc-frontend-sim 并平滑重启..."
    docker exec -u 0 soc-frontend-sim rm -rf /app/Desktop /app/Users /app/frontend /app/.next/server /app/.next/static 2>/dev/null || true
    docker cp "$app_src/." soc-frontend-sim:/app/
    if [ -d "$app_src/.next" ]; then
        docker cp "$app_src/.next" soc-frontend-sim:/app/
    fi
    # 嵌套布局时 node_modules 挂在 standalone 根上，需单独并入 /app/node_modules
    if [ "$app_src" != "$standalone_dir" ] && [ -d "$standalone_dir/node_modules" ]; then
        docker cp "$standalone_dir/node_modules/." soc-frontend-sim:/app/node_modules/
    fi
    docker cp "$ROOT_DIR/frontend/.next/static/." soc-frontend-sim:/app/.next/static/
    docker cp "$ROOT_DIR/frontend/public/." soc-frontend-sim:/app/public/ 2>/dev/null || true
    docker exec -u 0 soc-frontend-sim sh -c 'chown -R nextjs:nodejs /app/.next /app/node_modules /app/server.js /app/public 2>/dev/null; true'
    docker restart soc-frontend-sim >/dev/null

    # 确认服务真的起来再报成功，避免"报喜式崩溃"
    local fe_port="${HOST_PORT_FRONTEND:-13000}" i
    for i in $(seq 1 30); do
        if curl -fsSL -o /dev/null --max-time 2 "http://127.0.0.1:${fe_port}/" 2>/dev/null; then
            success "前端已完成极速更新并重新上线！(http://127.0.0.1:${fe_port})"
            return 0
        fi
        sleep 1
    done
    error "前端注入后 30s 内未就绪，请检查: docker logs soc-frontend-sim"
    return 1
}

# 快速更新后端
fast_update_backend() {
    info "正在平滑更新后端容器 soc-backend-sim..."
    cd "$ROOT_DIR"
    compose_sim up -d --force-recreate --no-deps backend
    success "后端容器已平滑重启上线！(http://127.0.0.1:18088)"
}

# 极速更新命令入口
cmd_update() {
    check_docker
    local target="${1:-all}"
    case "$target" in
        frontend)
            fast_update_frontend
            ;;
        backend)
            fast_update_backend
            ;;
        data)
            cmd_sync_data
            ;;
        all)
            info "执行全量智能极速同步 (前端产物 + 后端容器)..."
            fast_update_frontend
            fast_update_backend
            success "前端与后端已全部完成极速同步！(数据库已直连，数据天然实时一致)"
            ;;
        *)
            warn "未知更新目标: $target"
            echo "支持的目标: frontend | backend | data | all"
            exit 1
            ;;
    esac
}

# 全量 Docker 镜像构建（用于正式发布前的纯净全真验证）
cmd_build() {
    check_docker
    local target="${1:-all}"
    info "正在执行完整 Docker 镜像构建 (启用 BuildKit 缓存加速)..."
    cd "$ROOT_DIR"
    export DOCKER_BUILDKIT=1
    export COMPOSE_DOCKER_CLI_BUILD=1

    case "$target" in
        frontend)
            compose_sim build frontend
            docker rm -f soc-frontend-sim 2>/dev/null || true
            compose_sim up -d --no-deps frontend
            ;;
        backend)
            compose_sim build backend
            docker rm -f soc-backend-sim 2>/dev/null || true
            compose_sim up -d --no-deps backend
            ;;
        all)
            compose_sim build
            docker rm -f soc-frontend-sim soc-backend-sim 2>/dev/null || true
            compose_sim up -d
            ;;
        *)
            warn "未知构建目标: $target"
            echo "支持的目标: frontend | backend | all"
            exit 1
            ;;
    esac
    success "全量镜像构建并上线完成！"
    cmd_status
}

# 日志查看
cmd_logs() {
    check_docker
    local target="${1:-}"
    cd "$ROOT_DIR"
    case "$target" in
        frontend)
            docker logs -f soc-frontend-sim
            ;;
        backend)
            docker logs -f soc-backend-sim
            ;;
        postgres)
            docker logs -f soc-postgres-sim
            ;;
        redis)
            docker logs -f soc-redis-sim
            ;;
        *)
            compose_sim logs -f --tail 50
            ;;
    esac
}

# 启动前端文件自动监听守护 (Watch Mode)
cmd_watch() {
    check_docker
    info "启动前端代码保存自动同步守护 (Watch Mode)..."
    info "只要 frontend/ 目录下代码保存，将全自动增量编译并秒级热注入仿真前端容器。"
    ROOT_DIR="$ROOT_DIR" node -e '
      const fs = require("fs");
      const path = require("path");
      const { execSync } = require("child_process");
      let timer = null;
      const rootDir = process.env.ROOT_DIR || process.cwd();
      const targetDir = path.join(rootDir, "frontend");
      console.log("\x1b[36m[WATCHING]\x1b[0m 正在实时监听: " + targetDir);
      console.log("\x1b[33m[INFO]\x1b[0m 修改前端代码保存后，系统将自动触发极速同步，按 Ctrl+C 退出。\n");
      fs.watch(targetDir, { recursive: true }, (eventType, filename) => {
        if (!filename) return;
        if (filename.includes(".next") || filename.includes("node_modules") || filename.includes(".git")) return;
        if (!/\.(tsx?|jsx?|json|css)$/.test(filename)) return;
        clearTimeout(timer);
        timer = setTimeout(() => {
          console.log("\x1b[32m[DETECTED]\x1b[0m 文件变动: " + filename + "，正在自动增量更新仿真容器...");
          try {
            execSync("./Scripts/sim.sh update frontend", { stdio: "inherit", cwd: rootDir });
            console.log("\x1b[32m[DONE]\x1b[0m 仿真环境前端已全自动更新完成！\n");
          } catch (e) {
            console.error("\x1b[31m[ERROR]\x1b[0m 自动更新出错: " + e.message);
          }
        }, 1200);
      });
    '
}

# 主入口调度
main() {
    local action="${1:-help}"
    shift || true

    case "$action" in
        status)
            cmd_status
            ;;
        start|up)
            cmd_start
            ;;
        dev)
            cmd_dev
            ;;
        watch)
            cmd_watch
            ;;
        stop|down)
            cmd_stop
            ;;
        restart)
            cmd_restart
            ;;
        update|sync)
            cmd_update "$@"
            ;;
        sync-data)
            cmd_sync_data
            ;;
        build|rebuild)
            cmd_build "$@"
            ;;
        logs)
            cmd_logs "$@"
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            error "未知命令: $action"
            show_help
            exit 1
            ;;
    esac
}

main "$@"
