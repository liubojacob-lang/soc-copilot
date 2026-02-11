# GitHub Actions 配置指南

## ✅ 已完成的工作

1. ✅ GitHub Actions 工作流文件 (`.github/workflows/ci-cd.yml`)
2. ✅ Dockerfile (后端 + 前端)
3. ✅ docker-compose 配置 (开发 + 生产)
4. ✅ 部署脚本 (`deploy.sh`)
5. ✅ 测试框架 (pytest)
6. ✅ 代码已提交到 Git

## 🚀 下一步：配置 GitHub Secrets

### 1. 创建 GitHub 仓库

如果你还没有 GitHub 仓库，请创建：

```bash
# 在 GitHub 上创建新仓库
# 然后关联本地仓库
git remote add origin https://github.com/yourusername/soc-copilot.git
git push -u origin master
```

### 2. 配置 GitHub Secrets

进入 GitHub 仓库 → Settings → Secrets and variables → Actions

添加以下 Secrets：

| Secret Name | Value | Description |
|-------------|-------|-------------|
| `DOCKERHUB_USERNAME` | your-dockerhub-username | Docker Hub 用户名 |
| `DOCKERHUB_TOKEN` | your-dockerhub-token | Docker Hub 访问令牌 |

**获取 Docker Hub Token：**
1. 登录 https://hub.docker.com
2. Account Settings → Security → New Access Token
3. 复制 Token 并保存到 GitHub Secrets

### 3. 可选 Secrets

如果需要部署到服务器，添加：

| Secret Name | Value |
|-------------|-------|
| `SSH_HOST` | your-server-ip |
| `SSH_USERNAME` | your-username |
| `SSH_PRIVATE_KEY` | your-ssh-private-key |
| `DEPLOY_ENV` | staging/production |

## 🔄 CI/CD 流程说明

### 自动化流程

```
代码 Push → GitHub Actions 触发
    │
    ├─ 并行执行:
    │   ├─ 后端测试 (pytest)
    │   ├─ 前端测试 (npm test)
    │   └─ 安全扫描 (bandit, npm audit)
    │
    ├─ 构建 Docker 镜像
    │   ├─ soc-copilot-backend:latest
    │   └─ soc-copilot-frontend:latest
    │
    ├─ 推送到 Docker Hub
    │
    └─ 部署到服务器 (可选)
        ├─ Staging 环境
        └─ Production 环境
```

### 分支策略

| 分支 | 触发条件 | 部署目标 |
|------|----------|----------|
| `main` | push / PR | Production |
| `develop` | push / PR | Staging |
| `feature/*` | PR only | 不部署 |

## 🧪 本地测试 CI/CD

### 测试 GitHub Actions 本地运行

```bash
# 使用 act 工具本地测试
# 安装: https://github.com/nektos/act

# 测试 workflow
act push

# 测试特定 job
act push -j backend-tests
```

### 测试 Docker 构建

```bash
# 构建后端镜像
cd backend
docker build -t soc-copilot-backend:test .

# 构建前端镜像
cd frontend
docker build -t soc-copilot-frontend:test .

# 测试运行
docker-compose up -d
```

## 📊 监控 CI/CD 状态

### GitHub Actions 面板

访问: `https://github.com/yourusername/soc-copilot/actions`

### 徽章 (Badge)

在 README.md 中添加：

```markdown
![CI/CD](https://github.com/yourusername/soc-copilot/workflows/CI/CD%20Pipeline/badge.svg)
```

## 🛠️ 故障排查

### 常见问题

1. **Docker 登录失败**
   - 检查 `DOCKERHUB_USERNAME` 和 `DOCKERHUB_TOKEN`
   - 确保 Token 有读写权限

2. **测试失败**
   - 检查测试日志
   - 本地运行测试: `pytest backend/tests/`

3. **构建失败**
   - 检查 Dockerfile 语法
   - 查看构建日志中的错误信息

## 📋 验证清单

部署前确认：

- [ ] GitHub 仓库已创建
- [ ] GitHub Secrets 已配置
- [ ] Docker Hub Token 已生成
- [ ] 代码已推送到 GitHub
- [ ] CI/CD 流程运行成功
- [ ] Docker 镜像已推送到 Hub
- [ ] 部署脚本已测试

## 🎉 完成！

配置完成后，每次 Push 代码到 GitHub，CI/CD 会自动：
1. 运行测试
2. 构建 Docker 镜像
3. 推送到 Docker Hub
4. 部署到服务器 (如果配置了)

---

**下一步**: 查看 `DEPLOY.md` 进行生产环境部署。
