# 排障手册

## 适用对象

所有用户，开发、运维人员。

## 目标

快速定位并解决常见问题。

## 1. 剧本执行报 500 错误

### 排查步骤

```bash
# 1. 查看后端日志
tail -100 backend/backend.log | grep -i error

# 2. 查找具体错误
grep "run_id" backend.log

# 3. 检查数据库 (生产环境 PostgreSQL 15)
docker exec -it soc-copilot-postgres-prod psql -U ${DB_USER:-soc} -d ${DB_NAME:-soc} -c "SELECT id, status, started_at, completed_at, error_message FROM playbook_runs WHERE id='RUN-ID';"
# K8s 环境
kubectl exec -it deployment/backend -n soc-copilot -- psql $DATABASE_URL -c "SELECT id, status, started_at, completed_at, error_message FROM playbook_runs WHERE id='RUN-ID';"
```

### 常见原因

| 原因                   | 解决方案            |
| ---------------------- | ------------------- |
| 数据库连接超时         | 检查连接池水位，扩大 `max_connections` 或优化慢查询 |
| 外部 API 调用失败      | 检查网络/防火墙与断路器（Circuit Breaker）状态 |
| 剧本定义 JSON 格式错误 | 验证 YAML/JSON 语法与节点 Schema |
| 节点配置缺失           | 检查节点必填字段与参数映射 |

## 2. 前端 Maximum update depth exceeded

### 解决方案

```tsx
// ❌ 错误写法
useEffect(() => {
  setData(data); // 无限循环
}, [data]);

// ✅ 正确写法
useEffect(() => {
  const fetch = async () => {
    const result = await api.get("/data");
    setData(result);
  };
  fetch();
}, [id]);
```

## 3. OTX / 外部威胁情报与 AI 大模型调用异常

### 排查步骤

```bash
# 1. 检查 API Key 连通性
curl -H "X-OTX-API-KEY: $OTX_KEY" \
  https://otx.alienvault.com/api/v1/users/me

# 2. 检查大模型提供商 API 连通性
curl -X POST https://open.bigmodel.cn/api/paas/v4/chat/completions \
  -H "Authorization: Bearer $ZHIPU_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"glm-4-flash","messages":[{"role":"user","content":"ping"}]}'

# 3. 检查断路器（Circuit Breaker）状态与日志
docker logs soc-copilot-backend-prod --tail 200 | grep -i "circuitbreaker"
```

### 常见问题与降级处理

| 问题                  | 原因         | 解决方案       |
| --------------------- | ------------ | -------------- |
| 401 Unauthorized      | API Key 无效/过期 | 轮换并重新配置 Key |
| 429 Too Many Requests | 超过供应商速率限制 | 断路器将自动熔断并切入规则引擎降级模式（Rule-based Fallback） |
| Timeout / 连接挂起    | 网络抖动或供应商故障 | 默认 10s 超时后触发重试或熔断，无需手动重启 |

## 4. 生产数据库故障排查（PostgreSQL 15）

### 4.1 排查活跃连接数与长事务

```bash
# 查看当前活跃连接与运行超过 5 秒的事务
docker exec -it soc-copilot-postgres-prod psql -U ${DB_USER:-soc} -d ${DB_NAME:-soc} -c "
SELECT 
    pid, 
    now() - xact_start AS duration, 
    query, 
    state 
FROM pg_stat_activity 
WHERE state != 'idle' 
ORDER BY duration DESC 
LIMIT 10;
"
```

### 4.2 排查死锁与锁等待

```bash
# 查询正在被阻塞的进程与阻塞源 PID
docker exec -it soc-copilot-postgres-prod psql -U ${DB_USER:-soc} -d ${DB_NAME:-soc} -c "
SELECT 
    blocked_locks.pid     AS blocked_pid,
    blocked_activity.usename  AS blocked_user,
    blocking_locks.pid    AS blocking_pid,
    blocking_activity.usename AS blocking_user,
    blocked_activity.query    AS blocked_statement,
    blocking_activity.query   AS blocking_statement
FROM  pg_catalog.pg_locks         blocked_locks
JOIN pg_catalog.pg_stat_activity blocked_activity ON blocked_activity.pid = blocked_locks.pid
JOIN pg_catalog.pg_locks         blocking_locks 
    ON blocking_locks.locktype = blocked_locks.locktype
    AND blocking_locks.database IS NOT DISTINCT FROM blocked_locks.database
    AND blocking_locks.relation IS NOT DISTINCT FROM blocked_locks.relation
    AND blocking_locks.page IS NOT DISTINCT FROM blocked_locks.page
    AND blocking_locks.tuple IS NOT DISTINCT FROM blocked_locks.tuple
    AND blocking_locks.virtualxid IS NOT DISTINCT FROM blocked_locks.virtualxid
    AND blocking_locks.transactionid IS NOT DISTINCT FROM blocked_locks.transactionid
    AND blocking_locks.classid IS NOT DISTINCT FROM blocked_locks.classid
    AND blocking_locks.objid IS NOT DISTINCT FROM blocked_locks.objid
    AND blocking_locks.objsubid IS NOT DISTINCT FROM blocked_locks.objsubid
    AND blocking_locks.pid != blocked_locks.pid
JOIN pg_catalog.pg_stat_activity blocking_activity ON blocking_activity.pid = blocking_locks.pid
WHERE NOT blocked_locks.granted;
"
```

### 4.3 紧急终止卡死的阻塞事务

```bash
# 取消卡死的查询 (Graceful Cancel)
docker exec -it soc-copilot-postgres-prod psql -U ${DB_USER:-soc} -d ${DB_NAME:-soc} -c "SELECT pg_cancel_backend(<BLOCKING_PID>);"

# 强制终止卡死的后端会话 (Terminate)
docker exec -it soc-copilot-postgres-prod psql -U ${DB_USER:-soc} -d ${DB_NAME:-soc} -c "SELECT pg_terminate_backend(<BLOCKING_PID>);"
```

### 4.4 数据库迁移回滚与重试

```bash
# 检查当前 Alembic 迁移版本
docker exec -it soc-copilot-backend-prod alembic current

# 回滚上一版迁移 (执行 downgrade)
docker exec -it soc-copilot-backend-prod alembic downgrade -1

# 升级至最新版 (执行 upgrade)
docker exec -it soc-copilot-backend-prod alembic upgrade head
```

## 5. 消息队列与异步 Worker 积压排查（Redis）

### 5.1 查看队列深度与内存使用

```bash
# 检查告警处理队列长度
docker exec -it soc-copilot-redis-prod redis-cli -a ${REDIS_PASSWORD} LLEN alert:queue

# 查看 Redis 内存占用与连接数
docker exec -it soc-copilot-redis-prod redis-cli -a ${REDIS_PASSWORD} INFO memory
docker exec -it soc-copilot-redis-prod redis-cli -a ${REDIS_PASSWORD} INFO clients
```

### 5.2 紧急水平扩展 Worker 实例

```bash
# 动态将 alert-worker 从 3 节点扩容至 6 节点加速消费
docker compose -f docker-compose.prod.yml up -d --scale alert-worker=6
```

## 6. 其他常见问题

### 端口被占用

```bash
# Windows
netstat -ano | findstr :8000
taskkill /PID <PID> /F

# Linux/Mac
lsof -i :8000
kill -9 <PID>
```

### 跨域 (CORS) 错误

```python
# 检查后端 CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3003"],
)
```

## 日志位置汇总

| 服务 | 日志文件     | 位置      |
| ---- | ------------ | --------- |
| 后端 | backend.log  | backend/  |
| 前端 | frontend.log | frontend/ |
