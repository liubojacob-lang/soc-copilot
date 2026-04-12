# GitHub Copilot & AI Assistant 指南

## 代码生成原则

### 1. 类型安全优先

```typescript
// ✅ Good - 明确类型定义
interface AlertResponse {
  id: string;
  title: string;
  severity: "low" | "medium" | "high" | "critical";
}

async function fetchAlert(id: string): Promise<AlertResponse> {
  return api.get<AlertResponse>(`/alerts/${id}`);
}

// ❌ Bad - 使用 any
async function fetchAlert(id: string): Promise<any> {
  return api.get(`/alerts/${id}`);
}
```

### 2. 错误处理

```typescript
// ✅ Good - 完整错误处理
try {
  const result = await fetchData();
  return result;
} catch (error) {
  if (error instanceof NetworkError) {
    showToast("Network error. Please check your connection.", "error");
  } else {
    console.error("Failed to fetch data:", error);
    throw error;
  }
}

// ❌ Bad - 忽略错误
const result = await fetchData().catch(() => null);
```

### 3. 异步操作

```typescript
// ✅ Good - 并行请求
const [users, alerts, reports] = await Promise.all([fetchUsers(), fetchAlerts(), fetchReports()]);

// ❌ Bad - 串行请求
const users = await fetchUsers();
const alerts = await fetchAlerts();
const reports = await fetchReports();
```

## 组件开发规范

### React 组件结构

```tsx
// 1. 导入
import { useState, useEffect } from "react";
import { useTranslations } from "next-intl";

// 2. 类型定义
interface Props {
  id: string;
  onClose: () => void;
}

// 3. 组件定义
export function MyComponent({ id, onClose }: Props) {
  // 3.1 Hooks
  const t = useTranslations("namespace");
  const [data, setData] = useState<Data | null>(null);

  // 3.2 Effects
  useEffect(() => {
    loadData();
  }, [id]);

  // 3.3 事件处理
  const handleSubmit = async () => {
    // ...
  };

  // 3.4 渲染
  if (!data) return <LoadingSpinner />;

  return <div>{/* ... */}</div>;
}
```

### API 服务结构

```python
# 1. 导入
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

# 2. 路由定义
router = APIRouter(prefix="/api/v1/alerts", tags=["alerts"])

# 3. 依赖注入
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

# 4. 端点定义
@router.get("/{alert_id}")
async def get_alert(
    alert_id: str,
    db: AsyncSession = Depends(get_db)
):
    """获取告警详情"""
    # 业务逻辑
    pass
```

## 国际化规范

### 翻译键命名

```json
{
  "alerts": {
    "title": "告警管理",
    "createAlert": "创建告警",
    "noAlerts": "暂无告警",
    "severity": {
      "low": "低",
      "medium": "中",
      "high": "高",
      "critical": "严重"
    }
  }
}
```

### 使用方式

```tsx
// ✅ Good - 命名空间组织
const t = useTranslations("alerts");
return <h1>{t("title")}</h1>;

// ❌ Bad - 平铺
const t = useTranslations("common");
return <h1>{t("alertsTitle")}</h1>;
```

## 性能优化建议

### 1. 数据获取

- 使用 React Query 管理服务端状态
- 实现请求去重和缓存
- 使用 suspense 边界处理加载状态

### 2. 渲染优化

- 使用 `React.memo` 避免不必要渲染
- 使用 `useMemo` 和 `useCallback` 优化计算
- 实现虚拟列表处理大数据集

### 3. 代码分割

- 使用 `dynamic import` 懒加载组件
- 按路由拆分代码
- 优化第三方库导入

## 安全编码规范

### 1. 输入验证

```python
# ✅ Good - Pydantic 验证
class AlertCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    severity: Literal['low', 'medium', 'high', 'critical']
    description: Optional[str] = Field(None, max_length=2000)

# ❌ Bad - 无验证
@router.post("/alerts")
async def create_alert(data: dict):
    pass
```

### 2. SQL 注入防护

```python
# ✅ Good - 参数化查询
result = await db.execute(
    select(Alert).where(Alert.id == alert_id)
)

# ❌ Bad - 字符串拼接
query = f"SELECT * FROM alerts WHERE id = '{alert_id}'"
```

### 3. XSS 防护

```tsx
// ✅ Good - React 自动转义
<div>{userInput}</div>

// ❌ Bad - 直接插入HTML
<div dangerouslySetInnerHTML={{ __html: userInput }} />
```

## 测试规范

### 单元测试

```typescript
describe('AlertCard', () => {
  it('should display alert title', () => {
    render(<AlertCard alert={mockAlert} />);
    expect(screen.getByText(mockAlert.title)).toBeInTheDocument();
  });

  it('should handle click event', () => {
    const onClick = jest.fn();
    render(<AlertCard alert={mockAlert} onClick={onClick} />);
    fireEvent.click(screen.getByRole('button'));
    expect(onClick).toHaveBeenCalled();
  });
});
```

### API 测试

```python
@pytest.mark.asyncio
async def test_create_alert(client: AsyncClient, auth_headers: dict):
    response = await client.post(
        "/api/v1/alerts",
        json={"title": "Test Alert", "severity": "high"},
        headers=auth_headers
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Test Alert"
```

## Git 提交规范

### 提交消息格式

```
<type>(<scope>): <subject>

<body>

<footer>
```

### 类型说明

- `feat`: 新功能
- `fix`: Bug 修复
- `refactor`: 代码重构
- `docs`: 文档更新
- `test`: 测试相关
- `chore`: 构建/工具相关

### 示例

```
feat(alerts): add real-time alert streaming

- Implement WebSocket connection for real-time updates
- Add alert filtering by severity
- Display connection status indicator

Closes #123
```

## 文档规范

### 函数注释

```python
async def analyze_threat(
    indicators: List[str],
    provider: str = "zhipu"
) -> ThreatAnalysis:
    """
    分析威胁指标

    Args:
        indicators: 威胁指标列表 (IP/域名/Hash)
        provider: AI提供商 (zhipu/claude/openai)

    Returns:
        ThreatAnalysis: 威胁分析结果

    Raises:
        ValidationError: 指标格式无效
        AIServiceError: AI服务调用失败

    Example:
        >>> result = await analyze_threat(["192.168.1.1"])
        >>> print(result.threat_level)
        'high'
    """
```

### 组件文档

````tsx
/**
 * AlertCard - 告警卡片组件
 *
 * 显示单个告警的详细信息，支持点击查看详情
 *
 * @example
 * ```tsx
 * <AlertCard
 *   alert={alert}
 *   onClick={() => router.push(`/alerts/${alert.id}`)}
 *   size="md"
 * />
 * ```
 */
````
