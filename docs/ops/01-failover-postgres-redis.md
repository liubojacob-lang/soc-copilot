# SOC Copilot SRE Runbook: PostgreSQL & Redis 故障切换与灾备恢复指南

## 1. 适用场景与告警指标
- **告警名称**：`PostgresConnectionPoolExhausted` / `PostgresDown` / `RedisConnectionRefused`
- **影响范围**：核心告警入库阻塞、状态流转暂停、WebSocket 跨 Pod 广播降级为单机模式
- **SLA 目标**：RTO < 5 分钟，RPO < 1 分钟

---

## 2. 架构拓扑与高可用设计

```mermaid
graph TD
    API1[FastAPI Pod 1] --> HAProxy[DB / Redis Proxy]
    API2[FastAPI Pod 2] --> HAProxy
    HAProxy --> PG_Primary[(PostgreSQL Primary)]
    PG_Primary -.->|Streaming Replication| PG_Standby[(PostgreSQL Standby)]
    HAProxy --> Redis_Master[(Redis Master)]
    Redis_Master -.->|Replication| Redis_Replica[(Redis Replica)]
```

---

## 3. PostgreSQL 故障排查与主从切换 (Failover)

### 步骤 1: 存活确认与日志检查
```bash
# 检查主库容器运行状态
docker inspect soc-postgres --format='{{.State.Status}}'

# 查看 PostgreSQL 崩溃前最后 50 行日志
docker logs --tail 50 soc-postgres
```

### 步骤 2: 提升备库为主库 (Promote Standby)
若主库物理磁盘损坏或宿主机失联：
```bash
# 进入备库执行提升指令
docker exec -it soc-postgres-standby pg_ctl promote -D /var/lib/postgresql/data

# 验证当前节点已转变为可读写主库 (返回 f 表示不在恢复模式)
docker exec -it soc-postgres-standby psql -U postgres -d soc_copilot -c "SELECT pg_is_in_recovery();"
```

### 步骤 3: 路由重定向与后端环境变量热重载
更新连接字符串 `DATABASE_URL` 指向新主库 IP：
```bash
# 通过动态配置或负载均衡更新地址
export DATABASE_URL="postgresql+asyncpg://postgres:secure_password@new-pg-host:5432/soc_copilot"
```

---

## 4. Redis 故障恢复与持久化修复 (AOF / RDB)

### 步骤 1: 快速诊断
```bash
# 测试 Redis 响应
docker exec -it soc-redis redis-cli ping

# 查看持久化与内存统计
docker exec -it soc-redis redis-cli info persistence
docker exec -it soc-redis redis-cli info memory
```

### 步骤 2: AOF 文件损坏修复
如果 Redis 因断电出现 `Bad file format reading the append only file`:
```bash
# 运行修复工具自动截断损坏字节
docker exec -it soc-redis redis-check-aof --fix /data/appendonly.aof

# 重启 Redis 容器
docker restart soc-redis
```

---

## 5. 验证与业务回归检查单
- [ ] 执行 `curl -f http://localhost:8000/api/v1/health` 确认 DB 与 Redis 探针均为 `healthy`
- [ ] 检查 WebSocket 管理器已重新建立 Redis Pub/Sub 订阅
- [ ] 验证告警入库 `POST /api/v1/alerts/` 延迟低于 50ms
