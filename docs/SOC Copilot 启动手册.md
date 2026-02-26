# SOC Copilot 启动手册

## 启动服务

### 后端 (Backend)

```bash
# 方式1: 使用根目录脚本 (端口 8000)
npm run dev:backend

# 方式2: 直接运行
cd backend
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 前端 (Frontend)

```bash
# 方式1: 使用根目录脚本 (端口 3003)
npm run dev:frontend

# 方式2: 直接运行
cd frontend
npm run dev
```

### 一键启动 (前后端同时)

```bash
# 开发模式
npm run dev

# 生产模式
npm run start
```

---

## 端口占用处理

### 查看端口占用

```bash
# 查看 8000 端口 (后端)
lsof -i :8000

# 查看 3003 端口 (前端)
lsof -i :3003

# 查看所有占用端口
lsof -i :8000,3003
```

### 关闭占用端口

```bash
# 根据 PID 关闭 (替换 <PID> 为实际进程ID)
kill -9 <PID>

# 或使用端口号直接关闭
kill $(lsof -t -i :8000)
kill $(lsof -t -i :3003)

# 关闭所有相关进程
killall -9 python   # 后端
killall -9 node     # 前端
```

---

## 服务地址

| 服务 | 地址 |
|------|------|
| 后端 API | http://localhost:8000 |
| 前端界面 | http://localhost:3003 |
| API 文档 | http://localhost:8000/docs |
