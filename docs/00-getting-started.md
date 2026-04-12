# 🚀 快速开始指南

<div align="center">

![Quick Start](https://img.shields.io/badge/guide-quick%20start-brightgreen?style=for-the-badge&logo=rocket)
![Time](https://img.shields.io/badge/time-15%20minutes-blue?style=for-the-badge&logo=clock)

**⏱️ 15 分钟内完成环境搭建，启动 SOC Copilot**

</div>

---

## 📋 目录

- [适用对象](#-适用对象)
- [环境要求](#-环境要求)
- [快速启动](#-快速启动)
- [环境配置](#-环境配置)
- [故障排查](#-常见启动失败排查)
- [数据库初始化](#-数据库初始化)

---

## 👥 适用对象

> [!NOTE]
> 本指南面向首次部署 SOC Copilot 的**开发、运维人员**。

无需先验知识，按照步骤操作即可完成部署。

---

## 🎯 目标

15 分钟内完成开发环境搭建，能够正常运行前后端服务。

---

## 🛠️ 环境要求

<div align="center">

| 依赖                                                                                                         | 版本  | 说明       |  状态   |
| :----------------------------------------------------------------------------------------------------------- | :---- | :--------- | :-----: |
| ![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat-square&logo=python&logoColor=white)    | 3.10+ | 后端服务   | ✅ 必需 |
| ![Node.js](https://img.shields.io/badge/Node.js-18+-339933?style=flat-square&logo=nodedotjs&logoColor=white) | 18+   | 前端服务   | ✅ 必需 |
| ![Git](https://img.shields.io/badge/Git-2.0+-F05032?style=flat-square&logo=git&logoColor=white)              | 2.0+  | 版本控制   | ✅ 必需 |
| ![SQLite](https://img.shields.io/badge/SQLite-3.0+-003B57?style=flat-square&logo=sqlite&logoColor=white)     | 3.0+  | 开发数据库 | ✅ 内置 |

</div>

> [!TIP]
> 💡 推荐使用 [nvm](https://github.com/nvm-sh/nvm) 管理 Node.js 版本，[pyenv](https://github.com/pyenv/pyenv) 管理 Python 版本。

---

## ⚡ 快速启动

### 1️⃣ 克隆项目

```bash
# 克隆仓库
git clone https://github.com/your-org/soc-copilot.git

# 进入项目目录
cd soc-copilot
```

> [!TIP]
> 💡 如果 GitHub 访问较慢，可以使用镜像源或配置代理。

---

### 2️⃣ 启动后端服务

> [!IMPORTANT]
> 🔴 需要 Python 3.10+ 环境

```bash
# 进入后端目录
cd backend

# 创建虚拟环境
python -m venv venv

# 激活环境（Windows）
venv\Scripts\activate

# 激活环境（Mac/Linux）
# source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 启动服务
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

✅ **预期输出：**

```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete.
```

---

### 3️⃣ 启动前端服务

> [!IMPORTANT]
> 🔴 需要 Node.js 18+ 环境

打开**新的终端窗口**，执行：

```bash
# 进入前端目录
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

✅ **预期输出：**

```
ready - started server on 0.0.0.0:3003, url: http://localhost:3003
```

---

### 4️⃣ 访问应用

<div align="center">

| 🌐 服务      | 🔗 URL                     | 👤 默认账号          |
| :----------- | :------------------------- | :------------------- |
| **前端界面** | http://localhost:3003      | `admin` / `admin123` |
| **API 文档** | http://localhost:8000/docs | -                    |
| **数据库**   | `backend/data/app.db`      | -                    |

</div>

> [!CAUTION]
> ⚠️ **安全提醒**：首次登录后请立即修改默认密码！

---

## ⚙️ 环境配置

### 后端配置 `.env`

在 `backend/` 目录创建 `.env` 文件：

```env
# ============================================
# 🔐 安全密钥（生产环境务必修改！）
# ============================================
SECRET_KEY=your-secret-key-here-min-32-chars

# ============================================
# 🤖 AI Provider 配置
# ============================================
AI_PROVIDER=nvidia
NVIDIA_API_KEY=nvapi-your-nvidia-api-key
NVIDIA_MODEL=moonshotai/kimi-k2.5

# ============================================
# 🌐 AlienVault OTX（威胁情报）
# ============================================
OTX_API_KEY=your-otx-api-key

# ============================================
# 🔑 JWT 认证配置
# ============================================
JWT_SECRET_KEY=your-jwt-secret-key
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30

# ============================================
# 📝 日志配置
# ============================================
LOG_LEVEL=INFO
LOG_FILE=backend.log
```

---

### 前端配置 `.env.local`

在 `frontend/` 目录创建 `.env.local`：

```env
# API 后端地址
NEXT_PUBLIC_API_URL=http://localhost:8000
```

> [!TIP]
> 💡 如果后端使用不同端口，请相应修改 `NEXT_PUBLIC_API_URL`。

---

## 🔧 常见启动失败排查

<div align="center">

| ❌ 症状          | 🔍 原因          | ✅ 解决方案                                               |
| :--------------- | :--------------- | :-------------------------------------------------------- |
| 端口 8000 被占用 | 其他服务占用端口 | `netstat -ano \| findstr :8000` 查找并关闭                |
| pip 安装失败     | 网络超时         | `pip install --trusted-host pypi.org -r requirements.txt` |
| npm install 报错 | Node 版本不兼容  | 使用 nvm 切换到 Node 18+                                  |
| 数据库迁移失败   | SQLite 锁        | 删除 `data/*.db` 重新迁移                                 |
| CORS 跨域错误    | 前后端端口不一致 | 检查 `.env` 中的 API URL                                  |
| OTX 连接失败     | API Key 无效     | 确认 https://otx.alienvault.com 的 Key                    |

</div>

---

## 🗄️ 数据库初始化

首次启动会自动创建 SQLite 数据库：

```bash
# 进入后端目录
cd backend

# 初始化数据库
python migrate.py init

# 验证数据库
sqlite3 data/app.db ".tables"
```

✅ **预期输出：**

```
alembic_version
users
playbooks
alerts
...
```

---

## 🎉 下一步

<div align="center">

| 📖 推荐阅读                          | 🎯 目标       |
| :----------------------------------- | :------------ |
| [📗 架构总览](01-architecture.md)    | 理解系统设计  |
| [📙 API 文档](02-api-overview.md)    | 开始 API 集成 |
| [🛠️ 排障手册](10-troubleshooting.md) | 解决常见问题  |

</div>

---

<div align="center">

**🚀 恭喜！您已成功部署 SOC Copilot！**

[⬆️ 返回顶部](#-快速开始指南)

</div>
