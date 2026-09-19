# 运维部署手册（Production Operations）

> 2026-09-08 重写：与当前代码一致（PostgreSQL 15 + Redis 7 + docker compose v2 + k8s 可选）。
> 取代本文档早期基于 SQLite 单容器的叙述。适用对象：运维工程师、SRE、部署/维护管理员。

## 1. 拓扑

```
nginx(80/443, TLS) ─┬─ /api,/ws → backend (uvicorn, 4 workers)
                    └─ /        → frontend (Next.js standalone)
backend → postgres:15 (卷持久化) / redis:7 (AOF, 密码)
alert-worker ×3 → Redis Streams（通知派发）
可选：prometheus + grafana + loki/promtail（backend/docker-compose.grafana.yml）
```

## 2. 首次部署

```bash
# 1) 准备环境变量
cp .env.production.example .env.production
#    填写全部 CHANGE_ME 值（生成命令见模板注释）

# 2) 校验配置插值
docker compose --env-file .env.production -f docker-compose.prod.yml config -q

# 3) 构建并启动
docker compose --env-file .env.production -f docker-compose.prod.yml up -d --build

# 4) 迁移（容器启动时 AUTO_RUN_MIGRATIONS 默认执行；也可手动）
docker compose -f docker-compose.prod.yml exec -T backend alembic upgrade head

# 5) 健康检查
curl -f http://localhost/api/health        # → {"status":"ok"}
curl -f http://localhost/health/live
curl -f http://localhost/health/ready
```

`backend/Dockerfile` 自带 `HEALTHCHECK curl /api/health`；k8s 探针同路径。
本地开发（无 Docker）：见 `QUICKSTART.md`；SQLite 兜底库位于 `data/app.db`。

## 3. TLS 证书（Let's Encrypt）

前置：域名 A 记录指向本机，80 端口可从公网访问。

```bash
mkdir -p nginx/ssl nginx/certbot-www
docker compose --profile tls -f docker-compose.prod.yml run --rm certbot certonly \
  --webroot -w /var/www/certbot -d "$DOMAIN" \
  --email "$LETSENCRYPT_EMAIL" --agree-tos --no-eff-email
# 证书落盘 ./nginx/ssl/live/$DOMAIN/，按 nginx.prod.conf 引用路径链接，
# 重启 nginx；certbot 容器此后每 12h 自动续期
```

## 4. 备份与恢复

```bash
make db-backup                    # 备份至 backups/<时间戳>/（PG 或 SQLite 自动识别）
make db-restore FILE=backups/<时间戳>/app.db          # SQLite 恢复（需确认）
make db-restore FILE=backups/<时间戳>/postgres.sql.gz # PG 恢复（需确认）
```

- k8s 环境：`kubectl apply -f k8s/10-backup-cronjob.yaml`（每日 02:30 pg_dump → backup-pvc，保留 30 天）。
- **必须演练**：每季度执行一次「备份 → 删除 → 恢复 → 冒烟」闭环并记录。
- 备份不再打包环境变量快照（T1.3 安全加固，彻底杜绝明文密钥泄漏）；备份目录已在 `.gitignore` 中排除。

## 5. 监控

```bash
cd backend
GRAFANA_ADMIN_PASSWORD=xxx docker compose -f docker-compose.grafana.yml up -d
# Grafana http://localhost:3001（Prometheus 数据源与 SOC 面板自动 provisioning）
# Prometheus http://localhost:9090（告警规则挂载于 /etc/prometheus/rules/）
```

## 6. 发布与回滚

- 镜像按 `IMAGE_TAG` 版本化（`${DOCKERHUB_USERNAME}/soc-copilot-{backend,frontend}:$IMAGE_TAG`）。
- 回滚：`IMAGE_TAG=<上一版本> docker compose -f docker-compose.prod.yml up -d`；
  数据库回滚用 `alembic downgrade <已知良好 revision>`（回滚前先 `make db-backup`）。
- `Scripts/deploy/deploy.sh production` 封装备份→拉取→启动→迁移→健康检查。

## 7. 环境变量契约

- 全部必需变量见 `.env.production.example`（compose `:?` 守卫强制）。
- 生产启动校验（`STRICT_PRODUCTION_CHECKS=true`）会拒绝弱密钥/默认口令——`JWT_SECRET` ≥32 字符。
- 应用读取 `JWT_SECRET`（历史遗留的 `SECRET_KEY` 从未被代码使用，已从 compose 移除）。

## 8. 已知限制（截至 v0.9.4）

- 生产整机演练需在目标服务器执行一次（配置插值已验证通过）。
- k8s Secret 仍为 CHANGE_ME 占位，apply 前必须替换。
- 审计归档写本地容器卷，多副本部署时应改为共享/对象存储。

