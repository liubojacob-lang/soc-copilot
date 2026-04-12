# 🚀 SOC Copilot 快速启动指南 (v0.9.0)

## 前置要求

- Docker & Docker Compose v2.0+
- Python 3.12+ (仅开发模式)
- Node.js 20+ (仅开发模式)
- OpenSSL (生成密钥)

---

## 📦 首次安装 (5 分钟)

### 1. 克隆项目

```bash
git clone <repository-url>
cd sec
```

### 2. 生成安全密钥

```bash
# 数据库密码
export DB_PASSWORD=$(openssl rand -base64 32)

# JWT 密钥
export SECRET_KEY=$(openssl rand -base64 64)

# Redis 密码
export REDIS_PASSWORD=$(openssl rand -base64 32)

echo "✅ Keys generated!"
```

### 3. 生成 SSL 证书 (开发环境)

```bash
bash generate_ssl_cert.sh
```

### 4. 启动服务

**开发模式** (自动热重载):

```bash
docker-compose up -d
```

**生产模式** (使用 nginx):

```bash
docker-compose -f docker-compose.yml -f docker-compose.prod.yml --profile production up -d
```

### 5. 访问应用

| 服务     | URL                        | 说明       |
| -------- | -------------------------- | ---------- |
| 前端     | http://localhost:3003      | 用户界面   |
| 后端 API | http://localhost:8000      | REST API   |
| API 文档 | http://localhost:8000/docs | Swagger UI |

**默认管理员账号**:

- 用户名: `admin`
- 密码: 查看启动日志 (首次自动生成)

---

## 🔧 开发模式详解

### 目录结构

```
sec/
├── backend/              # FastAPI 后端
│   ├── routers/         # API 路由
│   ├── models/          # 数据库模型
│   ├── services/        # 业务逻辑
│   └── main.py          # 应用入口
├── frontend/            # Next.js 前端
│   ├── app/            # 页面路由
│   ├── components/     # React 组件
│   └── stores/         # 状态管理
├── nginx/              # Nginx 配置
├── docker-compose.yml  # 主配置
└── docker-compose.override.yml  # 开发覆盖配置
```

### 直接开发 (不使用 Docker)

**后端**:

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
python -m uvicorn main:app --reload --port 8000
```

**前端**:

```bash
cd frontend
npm install
npm run dev  # http://localhost:3003
```

---

## 🛡️ 安全配置

### 环境变量清单

复制并编辑 `.env` 文件:

```bash
cp .env.example .env
```

**必需变量**:

- `DB_PASSWORD` - 数据库密码 (最小 16 字符)
- `SECRET_KEY` - JWT 密钥 (最小 32 字符)
- `REDIS_PASSWORD` - Redis 密码 (最小 16 字符)

**可选变量**:

- `CORS_ORIGINS` - CORS 白名单 (逗号分隔)
- `AI_PROVIDER` - AI 提供商 (`anthropic` 或 `zhipu`)
- `ZHIPU_API_KEY` - 智谱 AI 密钥
- `ANTHROPIC_API_KEY` - Claude API 密钥

### 安全扫描

**安装 pre-commit hooks**:

```bash
pip install pre-commit
pre-commit install
```

**手动扫描**:

```bash
pre-commit run --all-files
```

---

## 🐳 Docker 命令速查

```bash
# 启动
docker-compose up -d

# 查看日志
docker-compose logs -f backend

# 停止
docker-compose down

# 重置数据库
docker-compose down -v
docker-compose up -d

# 进入容器
docker exec -it soc-copilot-backend bash

# 查看网络
docker network ls
docker network inspect sec_backend-net
```

---

## 🔍 故障排查

### 启动失败: DB_PASSWORD 错误

**问题**: `ERROR: DB_PASSWORD environment variable is required`

**解决**:

```bash
export DB_PASSWORD=$(openssl rand -base64 32)
docker-compose up -d
```

### CORS 错误: Origin not allowed

**问题**: 前端无法连接后端

**解决**: 设置 CORS_ORIGINS:

```bash
export CORS_ORIGINS=http://localhost:3003
docker-compose up -d
```

### 数据库连接失败

**问题**: `could not connect to server`

**解决**:

```bash
# 检查数据库是否启动
docker-compose ps postgres

# 查看日志
docker-compose logs postgres
```

### SSL 证书错误

**问题**: Nginx 启动失败

**解决**:

```bash
bash generate_ssl_cert.sh
docker-compose restart nginx
```

---

## 📚 更多文档

- [安全优化报告](./SECURITY_OPTIMIZATION_SUMMARY.md)
- [安全修复报告](./SECURITY_FIX_REPORT.md)
- [API 文档](http://localhost:8000/docs)
- [手动测试指南](./MANUAL_TEST.md)
- [测试用例](./TEST_CASES.md)

---

## 🆘 获取帮助

1. 查看日志: `docker-compose logs -f`
2. 检查状态: `docker-compose ps`
3. 验证健康: `curl http://localhost:8000/api/health`

---

**版本**: v0.9.0  
**最后更新**: 2026-04-09
