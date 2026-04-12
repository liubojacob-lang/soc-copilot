# SOC Copilot - 项目上下文文档

## 项目概述

- **项目名称**: SOC Copilot
- **版本**: v0.8.2
- **类型**: 安全运营中心(SOC)智能化平台
- **技术栈**: FastAPI + Next.js 16 + SQLite/PostgreSQL + Redis

## 核心架构

### 前端 (Port 3003)

- 框架: Next.js 16 with App Router
- 语言: TypeScript 5
- 状态管理: React Query + Zustand
- UI: Tailwind CSS + Lucide Icons
- 国际化: next-intl (en/zh)

### 后端 (Port 8000)

- 框架: FastAPI (Python 3.11+)
- ORM: SQLAlchemy 2.0 (异步)
- 认证: JWT + HttpOnly Cookies
- AI集成: 多厂商 (Zhipu/Claude/OpenAI)

### 数据层

- 开发: SQLite (单文件)
- 生产: PostgreSQL 15+
- 缓存: Redis 7+ (可选)

## 关键技术决策

### 已选型

1. **App Router** - 现代化路由，SSR/SSG混合
2. **Pydantic v2** - 类型安全验证
3. **React Query** - 服务端状态管理
4. **SQLAlchemy 2.0** - 异步ORM

### 待优化

1. **SQLite → PostgreSQL** - 生产必须迁移
2. **内存缓存 → Redis** - 多实例共享
3. **单AI厂商 → 多厂商路由** - 容错能力

## 代码规范

### TypeScript

- 严格模式: `strict: true`
- 类型覆盖目标: 80%+
- 禁止 `any` (除非必要)

### Python

- 类型注解: 必须
- 文档字符串: 公共API必须
- 测试覆盖: 核心逻辑 60%+

### 命名约定

- 组件: PascalCase (AlertCard.tsx)
- 函数: camelCase (loadAuthState)
- 常量: UPPER_SNAKE_CASE (CACHE_VERSION)
- 文件: kebab-case (ai-service.ts)

## 开发流程

### 分支策略

- `main`: 生产分支，受保护
- `develop`: 开发分支
- `feature/*`: 功能分支
- `fix/*`: 修复分支

### 提交规范

```
feat: 新功能
fix: 修复bug
refactor: 重构
docs: 文档
test: 测试
chore: 构建/工具
```

### 代码审查

- 必须通过 TypeScript 编译
- 必须通过 ESLint 检查
- 核心功能需要测试

## 常见问题

### Q: 如何运行项目？

```bash
# 后端
cd backend && source venv/bin/activate
uvicorn main:app --reload --port 8000

# 前端
cd frontend && npm run dev
```

### Q: 如何添加新翻译？

1. 在 `frontend/messages/en/*.json` 添加英文
2. 在 `frontend/messages/zh/*.json` 添加中文
3. 使用 `useTranslations('namespace')` 调用

### Q: 如何添加新API端点？

1. 在 `backend/api/v1/` 创建路由文件
2. 在 `backend/services/` 创建业务逻辑
3. 在 `backend/models/` 定义数据模型
4. 更新 API 文档

## 性能基准

### 当前指标

- 首屏加载: 3-5秒 (目标 <2秒)
- API P99: 500-800ms (目标 <200ms)
- 构建时间: ~10分钟

### 优化重点

1. 数据库查询优化
2. 前端代码分割
3. AI调用并行化
4. 缓存策略优化

## 安全注意事项

### 必须配置

- JWT_SECRET: 32+ 字符随机字符串
- BOOTSTRAP_ADMIN_PASSWORD: 12+ 字符
- SECRET_ENCRYPTION_KEY: Fernet密钥

### 禁止行为

- 提交敏感信息到 Git
- 在生产环境使用默认密码
- 禁用 HTTPS

## 联系方式

- 项目维护: SOC Team
- 技术支持: tech@example.com
