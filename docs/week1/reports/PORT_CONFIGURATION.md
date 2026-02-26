# 端口配置 - SOC Copilot

**固定端口配置** - 请严格遵守

---

## 🚨 重要说明

**所有环境的前端端口固定为: `3003`**

---

## 📋 端口分配

| 服务 | 端口 | 说明 |
|------|------|------|
| **后端 API** | `8000` | FastAPI 服务 |
| **前端 UI** | `3003` | Next.js 开发服务器 |
| **WebSocket** | `8000` | 与后端共享 |

---

## 🚀 启动命令

### 开发环境

```bash
# 后端
cd backend
python main.py
# 运行在: http://localhost:8000

# 前端
cd frontend
npm run dev -- -p 3003
# 运行在: http://localhost:3003
```

### 生产环境

```bash
# 使用 Docker Compose
docker-compose up -d

# 或使用生产配置
docker-compose -f docker-compose.prod.yml up -d
```

---

## ⚙️ 配置文件

### Next.js 配置

```javascript
// frontend/next.config.js
module.exports = {
  devServer: {
    port: 3003
  }
}
```

### 环境变量

```bash
# frontend/.env.local
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000
NEXT_PUBLIC_PORT=3003
```

### NPM Scripts

```json
// frontend/package.json
{
  "scripts": {
    "dev": "next dev -p 3003",
    "build": "next build",
    "start": "next start -p 3003",
    "lint": "next lint"
  }
}
```

---

## 🔒 固定端口的原因

1. **一致性**: 开发、测试、生产环境使用相同端口
2. **文档**: 所有文档和测试脚本统一使用 3003
3. **避免冲突**: 3003 不常用，减少端口冲突
4. **WebSocket**: 与后端 8000 端口分离，避免混淆

---

## 📝 更新日志

| 日期 | 端口 | 原因 |
|------|------|------|
| 2026-02-25 | `3003` | 固定前端端口 |

---

## ⚠️ 注意事项

1. **不要修改**: 除非经过团队讨论，否则不要修改端口
2. **文档同步**: 修改端口时同步更新所有文档
3. **防火墙**: 确保 3003 端口在防火墙中开放
4. **代理**: 生产环境可能需要反向代理配置

---

## 🔧 故障排除

### 端口已被占用

```bash
# 查找占用端口的进程
lsof -i :3003

# 杀死进程
kill -9 <PID>

# 或使用其他端口 (临时)
npm run dev -- -p 3004
```

### Docker 端口映射

```yaml
# docker-compose.yml
services:
  frontend:
    ports:
      - "3003:3000"  # 宿主机:容器
```

---

## 📞 支持

如有端口配置问题，请查看:
- `docker-compose.yml`
- `frontend/next.config.js`
- `frontend/package.json`

---

**最后更新**: 2026-02-25
**维护者**: SOC Copilot Team
