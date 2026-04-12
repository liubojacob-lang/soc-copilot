# SOC Copilot 最佳实践指南

## 目录

1. [项目配置体系](#项目配置体系)
2. [代码质量标准](#代码质量标准)
3. [开发工作流](#开发工作流)
4. [团队协作规范](#团队协作规范)
5. [自动化工具](#自动化工具)

---

## 1. 项目配置体系

### 1.1 配置文件清单

| 文件                              | 用途              | 重要性     |
| --------------------------------- | ----------------- | ---------- |
| `.claude/CLAUDE.md`               | 项目上下文文档    | ⭐⭐⭐⭐⭐ |
| `AGENTS.md`                       | 开发代理指南      | ⭐⭐⭐⭐⭐ |
| `.github/copilot-instructions.md` | AI协作指南        | ⭐⭐⭐⭐   |
| `.eslintrc.json`                  | 代码检查配置      | ⭐⭐⭐⭐⭐ |
| `.prettierrc`                     | 代码格式化配置    | ⭐⭐⭐⭐   |
| `.editorconfig`                   | 编辑器统一配置    | ⭐⭐⭐⭐   |
| `.vscode/settings.json`           | VS Code工作区配置 | ⭐⭐⭐⭐   |
| `Makefile`                        | 便捷命令集        | ⭐⭐⭐⭐   |
| `package.json`                    | 项目依赖和脚本    | ⭐⭐⭐⭐⭐ |
| `tsconfig.json`                   | TypeScript配置    | ⭐⭐⭐⭐⭐ |

### 1.2 快速启动命令

```bash
# 开发环境
make dev

# 代码检查
make lint

# 代码格式化
make format

# 类型检查
make type-check

# 运行测试
make test

# 清理构建
make clean
```

---

## 2. 代码质量标准

### 2.1 TypeScript 规范

#### 类型安全

```typescript
// ✅ 推荐：明确的类型定义
interface User {
  id: string;
  name: string;
  email: string;
  role: "admin" | "analyst" | "auditor";
}

async function fetchUser(id: string): Promise<User> {
  return api.get<User>(`/users/${id}`);
}

// ❌ 避免：使用 any
async function fetchUser(id: string): Promise<any> {
  return api.get(`/users/${id}`);
}
```

#### 避免空值

```typescript
// ✅ 推荐：可选链和空值合并
const userName = user?.profile?.name ?? "Unknown";

// ❌ 避免：直接访问可能为空的属性
const userName = user.profile.name;
```

#### 泛型约束

```typescript
// ✅ 推荐：泛型约束
function getProperty<T, K extends keyof T>(obj: T, key: K): T[K] {
  return obj[key];
}

// ❌ 避免：无约束的泛型
function getProperty(obj: any, key: string): any {
  return obj[key];
}
```

### 2.2 React 最佳实践

#### 组件结构

```tsx
// 1. 导入
import { useState, useEffect } from "react";
import { useTranslations } from "next-intl";

// 2. 类型定义
interface Props {
  title: string;
  onClose: () => void;
}

// 3. 组件定义
export function MyComponent({ title, onClose }: Props) {
  // 3.1 Hooks
  const t = useTranslations("namespace");
  const [data, setData] = useState<string>("");

  // 3.2 Effects
  useEffect(() => {
    // ...
  }, []);

  // 3.3 事件处理
  const handleClick = () => {
    // ...
  };

  // 3.4 渲染
  return <div>{/* ... */}</div>;
}
```

#### 性能优化

```tsx
// ✅ 推荐：使用 memo 避免不必要的渲染
import { memo } from "react";

export const AlertCard = memo(function AlertCard({ alert }: Props) {
  return <div>{alert.title}</div>;
});

// ✅ 推荐：使用 useMemo 缓存计算结果
const sortedAlerts = useMemo(() => {
  return alerts.sort((a, b) => b.severity - a.severity);
}, [alerts]);

// ✅ 推荐：使用 useCallback 缓存回调
const handleClick = useCallback(() => {
  onSelect(alert.id);
}, [alert.id, onSelect]);
```

### 2.3 Python 规范

#### 类型注解

```python
from typing import Optional, List
from pydantic import BaseModel

# ✅ 推荐：完整的类型注解
class Alert(BaseModel):
    id: str
    title: str
    severity: Literal['low', 'medium', 'high', 'critical']
    description: Optional[str] = None

async def fetch_alert(alert_id: str) -> Alert:
    return await db.get(Alert, alert_id)

# ❌ 避免：缺少类型注解
async def fetch_alert(alert_id):
    return await db.get(Alert, alert_id)
```

#### 异步编程

```python
# ✅ 推荐：并行异步操作
results = await asyncio.gather(
    fetch_alerts(),
    fetch_users(),
    fetch_reports()
)

# ❌ 避免：串行异步操作
alerts = await fetch_alerts()
users = await fetch_users()
reports = await fetch_reports()
```

---

## 3. 开发工作流

### 3.1 功能开发流程

```
┌─────────────┐
│ 1. 创建分支 │
└──────┬──────┘
       │
┌──────┴──────┐
│ 2. 编写代码 │
└──────┬──────┘
       │
┌──────┴──────┐
│ 3. 本地测试 │
└──────┬──────┘
       │
┌──────┴──────┐
│ 4. 代码检查 │
└──────┬──────┘
       │
┌──────┴──────┐
│ 5. 提交代码 │
└──────┬──────┘
       │
┌──────┴──────┐
│ 6. 创建 PR  │
└──────┬──────┘
       │
┌──────┴──────┐
│ 7. 代码审查 │
└──────┬──────┘
       │
┌──────┴──────┐
│ 8. 合并代码 │
└─────────────┘
```

### 3.2 Git 提交规范

```
<type>(<scope>): <subject>

<body>

<footer>
```

#### 类型说明

- `feat`: 新功能
- `fix`: Bug修复
- `refactor`: 代码重构
- `docs`: 文档更新
- `test`: 测试相关
- `chore`: 构建/工具

#### 示例

```
feat(alerts): add real-time alert streaming

- Implement WebSocket connection for real-time updates
- Add alert filtering by severity
- Display connection status indicator

Closes #123
```

### 3.3 分支命名规范

```
feature/<功能名称>   # 新功能
fix/<问题描述>       # Bug修复
refactor/<重构内容>  # 重构
docs/<文档内容>      # 文档
```

**示例：**

- `feature/alert-streaming`
- `fix/login-auth-error`
- `refactor/api-error-handling`
- `docs/api-documentation`

---

## 4. 团队协作规范

### 4.1 代码审查清单

#### 前端审查

- [ ] 类型安全：无 `any` 类型
- [ ] 性能：使用 `memo`、`useMemo`、`useCallback`
- [ ] 可访问性：ARIA 属性、键盘导航
- [ ] 国际化：所有文案使用 `useTranslations`
- [ ] 错误处理：完整的 try-catch
- [ ] 测试：关键逻辑有单元测试

#### 后端审查

- [ ] 类型注解：所有函数有类型注解
- [ ] API文档：更新 OpenAPI 文档
- [ ] 安全：输入验证、SQL注入防护
- [ ] 性能：数据库查询优化
- [ ] 错误处理：异常捕获和日志
- [ ] 测试：核心逻辑有单元测试

### 4.2 文档规范

#### README 结构

```markdown
# 项目名称

## 简介

项目简介和核心功能

## 快速开始

### 环境要求

### 安装步骤

### 运行命令

## 项目结构

目录结构说明

## 开发指南

### 代码规范

### 提交规范

### 分支策略

## API文档

API端点说明

## 部署指南

生产环境部署步骤

## 常见问题

FAQ

## 贡献指南

如何参与开发

## 许可证

开源协议
```

### 4.3 沟通协作

#### 每日站会

- 昨天：完成了什么
- 今天：计划做什么
- 阻碍：遇到什么问题

#### 代码评审会议

- 时间：每周一次
- 内容：代码质量、架构讨论
- 产出：改进建议、技术债务

#### 技术分享

- 频率：每月一次
- 主题：新技术、最佳实践、踩坑经验

---

## 5. 自动化工具

### 5.1 Pre-commit Hook

项目已配置 Git pre-commit hook，在每次提交前自动运行：

1. TypeScript 类型检查
2. ESLint 代码检查
3. 代码格式检查

### 5.2 CI/CD 配置建议

#### GitHub Actions 工作流

```yaml
name: CI

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
        with:
          node-version: "20"
          cache: "npm"
      - run: npm ci
      - run: npm run lint
      - run: npm run type-check
      - run: npm run test

  backend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: "3.11"
      - run: pip install -r requirements.txt
      - run: ruff check .
      - run: pytest
```

### 5.3 开发工具推荐

#### VS Code 扩展

- **ESLint** - 代码检查
- **Prettier** - 代码格式化
- **GitHub Copilot** - AI 编程助手
- **Tailwind CSS IntelliSense** - CSS 智能提示
- **GitLens** - Git 增强
- **EditorConfig** - 编辑器配置

#### Chrome 扩展

- **React Developer Tools** - React 调试
- **Redux DevTools** - 状态管理调试

---

## 6. 常见问题

### Q1: 如何添加新的翻译？

1. 在 `frontend/messages/en/*.json` 添加英文
2. 在 `frontend/messages/zh/*.json` 添加中文
3. 使用 `useTranslations('namespace')` 调用

### Q2: 如何添加新的API端点？

1. 在 `backend/models/` 定义数据模型
2. 在 `backend/services/` 创建业务逻辑
3. 在 `backend/api/v1/` 创建路由
4. 更新 API 文档

### Q3: 如何运行测试？

```bash
# 运行所有测试
make test

# 运行前端测试
make test-frontend

# 运行后端测试
make test-backend

# 运行E2E测试
make test-e2e
```

### Q4: 如何修复类型错误？

```bash
# 检查类型错误
make type-check

# 自动修复部分错误
cd frontend && npm run lint:fix
```

### Q5: 如何格式化代码？

```bash
# 格式化所有代码
make format

# 仅格式化前端
cd frontend && npm run format

# 仅格式化后端
cd backend && black . && isort .
```

---

## 7. 性能优化建议

### 7.1 前端优化

#### 代码分割

```typescript
// ✅ 推荐：动态导入
const HeavyComponent = dynamic(() => import('./HeavyComponent'), {
  loading: () => <Loading />,
  ssr: false
});

// ❌ 避免：静态导入大组件
import HeavyComponent from './HeavyComponent';
```

#### 虚拟列表

```typescript
import { FixedSizeList } from 'react-window';

// 渲染大量数据
<FixedSizeList
  height={600}
  itemCount={10000}
  itemSize={35}
  width="100%"
>
  {({ index, style }) => (
    <div style={style}>Item {index}</div>
  )}
</FixedSizeList>
```

### 7.2 后端优化

#### 数据库查询

```python
# ✅ 推荐：只查询需要的字段
result = await db.execute(
    select(Alert.id, Alert.title).where(Alert.status == 'open')
)

# ❌ 避免：查询所有字段
result = await db.execute(select(Alert))
```

#### 缓存策略

```python
from functools import lru_cache

@lru_cache(maxsize=128)
def get_cached_data(key: str) -> Any:
    return expensive_operation(key)
```

---

## 8. 安全最佳实践

### 8.1 输入验证

```typescript
// ✅ 推荐：使用 Zod 验证
import { z } from "zod";

const schema = z.object({
  title: z.string().min(1).max(200),
  severity: z.enum(["low", "medium", "high", "critical"]),
});

const result = schema.parse(input);
```

### 8.2 XSS 防护

```tsx
// ✅ 推荐：React 自动转义
<div>{userInput}</div>

// ❌ 避免：直接插入HTML
<div dangerouslySetInnerHTML={{ __html: userInput }} />

// 如果必须使用，先清理
import DOMPurify from 'dompurify';
<div dangerouslySetInnerHTML={{
  __html: DOMPurify.sanitize(userInput)
}} />
```

### 8.3 SQL 注入防护

```python
# ✅ 推荐：使用 ORM 参数化
result = await db.execute(
    select(Alert).where(Alert.id == alert_id)
)

# ❌ 避免：字符串拼接
query = f"SELECT * FROM alerts WHERE id = '{alert_id}'"
```

---

## 9. 监控与日志

### 9.1 日志规范

#### 前端日志

```typescript
// 开发环境
console.log("[AlertComponent] Fetching alerts...");

// 生产环境
logger.info("Alert fetched successfully", { alertId, count });
logger.error("Failed to fetch alerts", { error: error.message });
```

#### 后端日志

```python
import logging

logger = logging.getLogger(__name__)

logger.info("Alert created", extra={"alert_id": alert.id})
logger.error("Failed to create alert", exc_info=True)
```

### 9.2 性能监控

#### Web Vitals

```typescript
import { getCLS, getFID, getFCP, getLCP, getTTFB } from "web-vitals";

getCLS(console.log);
getFID(console.log);
getFCP(console.log);
getLCP(console.log);
getTTFB(console.log);
```

---

## 10. 总结

本最佳实践指南涵盖了 SOC Copilot 项目开发的各个方面，包括：

- 完整的配置体系
- 严格的代码质量标准
- 清晰的开发流程
- 团队协作规范
- 自动化工具链

遵循这些最佳实践将帮助团队：

- 提高代码质量
- 加速开发效率
- 降低维护成本
- 确保项目可扩展性

**持续改进是关键！** 定期审视和更新这些实践以适应项目发展。

---

**文档版本**: v1.0  
**最后更新**: 2026-04-10  
**维护者**: SOC Copilot Team
