# SOC Copilot 部署指南

## 本周完成的工作

### ✅ 1. 配置持久化修复
- **问题**: 前端保存的配置只保存在内存中，重启后丢失
- **解决**: 实现了 `.env` 文件自动写入机制
- **文件**: `backend/routers/admin_settings.py`

### ✅ 2. 单元测试框架
- **框架**: pytest + pytest-asyncio
- **覆盖率目标**: 60%
- **测试文件**:
  - `backend/tests/conftest.py` - 测试配置和fixtures
  - `backend/tests/test_core.py` - 核心功能测试
  - `backend/pytest.ini` - pytest配置

### ✅ 3. CI/CD 流水线
- **平台**: GitHub Actions
- **工作流**:
  - 后端测试 (Python)
  - 前端测试 (Node.js)
  - 安全扫描 (Bandit, npm audit)
  - Docker镜像构建和推送
  - 自动部署到Staging/Production

## 快速开始

### 本地开发

```bash
# 1. 克隆代码
git clone <repository-url>
cd soc-copilot

# 2. 启动服务
docker-compose up -d

# 3. 访问应用
# 前端: http://localhost:3000
# 后端: http://localhost:8000
# API文档: http://localhost:8000/docs
```

### 生产部署

```bash
# 1. 配置环境变量
cp .env.example .env.prod
# 编辑 .env.prod 文件，填写生产环境配置

# 2. 部署
./deploy.sh production
```

## 环境变量配置

### 必需配置
```env
# 数据库
DB_USER=soc_copilot
DB_PASSWORD=your-secure-password
DB_NAME=soc_copilot

# 安全配置
SECRET_KEY=your-secret-key-here

# Dify集成（可选）
DIFY_API_URL=http://your-dify-server/v1
DIFY_API_KEY=your-dify-api-key
```

## CI/CD 配置

### GitHub Secrets 配置
在 GitHub 仓库设置中添加以下 secrets：

- `DOCKERHUB_USERNAME` - Docker Hub 用户名
- `DOCKERHUB_TOKEN` - Docker Hub 访问令牌

### 分支策略
- `main` - 生产分支，自动部署到生产环境
- `develop` - 开发分支，自动部署到测试环境
- `feature/*` - 功能分支，运行测试但不部署

## 监控和日志

### 查看日志
```bash
# 查看所有服务日志
docker-compose logs -f

# 查看特定服务
docker-compose logs -f backend
docker-compose logs -f frontend
```

### 健康检查
```bash
# 检查后端健康状态
curl http://localhost:8000/api/health

# 检查前端
curl http://localhost:3000/api/health
```

## 备份和恢复

### 数据库备份
```bash
# 自动备份（每日执行）
docker-compose exec postgres pg_dump -U soc_copilot soc_copilot > backup_$(date +%Y%m%d).sql

# 恢复备份
docker-compose exec -T postgres psql -U soc_copilot soc_copilot < backup_20240211.sql
```

## 故障排查

### 常见问题

1. **端口被占用**
   ```bash
   # 检查端口占用
   netstat -tulpn | grep :8000
   
   # 停止占用端口的进程
   kill -9 <PID>
   ```

2. **数据库连接失败**
   ```bash
   # 检查数据库状态
   docker-compose ps postgres
   
   # 查看数据库日志
   docker-compose logs postgres
   ```

3. **权限问题**
   ```bash
   # 修复文件权限
   chmod +x deploy.sh
   ```

## 下一步计划

### Phase 2: AI赋能（下周开始）
1. AI告警分析助手
2. 自然语言查询
3. 智能Playbook推荐

### Phase 3: 高级功能
1. UEBA行为分析
2. 威胁狩猎平台
3. 威胁情报升级

---

**部署完成！** 🎉

如有问题，请查看日志或联系开发团队。
