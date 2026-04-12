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

# 3. 检查数据库
sqlite3 data/app.db "SELECT * FROM playbook_runs WHERE id='RUN-ID';"
```

### 常见原因

| 原因                   | 解决方案            |
| ---------------------- | ------------------- |
| 数据库连接超时         | 增加连接池大小      |
| 外部 API 调用失败      | 检查网络/防火墙     |
| 剧本定义 JSON 格式错误 | 验证 YAML/JSON 语法 |
| 节点配置缺失           | 检查节点必填字段    |

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

## 3. OTX 查询失败

```bash
# 1. 检查 API Key
curl -H "X-OTX-API-KEY: $OTX_KEY" \
  https://otx.alienvault.com/api/v1/users/me

# 2. 检查网络连通性
curl -v https://otx.alienvault.com
```

### 常见问题

| 问题                  | 原因         | 解决方案       |
| --------------------- | ------------ | -------------- |
| 401 Unauthorized      | API Key 无效 | 重新配置 Key   |
| 429 Too Many Requests | 超过速率限制 | 等待或升级套餐 |
| Timeout               | 网络问题     | 检查防火墙     |

## 4. 数据库问题

### 锁等待超时

```bash
# 查看当前锁
sqlite3 data/app.db ".locks"

# 解决：重启服务
pkill -f uvicorn
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 迁移失败

```bash
# 回滚到上一版本
alembic downgrade -1

# 重新迁移
alembic upgrade head
```

## 5. 其他常见问题

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
