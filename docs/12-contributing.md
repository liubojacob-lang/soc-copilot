# 贡献指南

## 适用对象

开发者、文档工程师、安全研究人员。

## 代码规范

### Python

遵循 PEP 8 + PEP 484：

```python
from typing import Dict, List, Optional
from pydantic import BaseModel, Field

class AlertInput(BaseModel):
    raw_log: str = Field(..., description="原始日志内容")
    alert_id: Optional[str] = None

async def analyze_alert(input_data: AlertInput) -> Dict[str, any]:
    """
    分析告警内容

    Args:
        input_data: 告警输入

    Returns:
        分析结果字典
    """
    pass
```

### TypeScript

遵循 ESLint + TypeScript 严格模式：

```typescript
interface Alert {
  id: string;
  name: string;
  severity: "critical" | "high" | "medium" | "low";
}

async function fetchAlert(id: string): Promise<Alert> {
  const response = await api.get(`/alerts/${id}`);
  return response.data;
}
```

## Git Commit 规范

### 提交格式

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Type 类型

| 类型       | 说明      |
| ---------- | --------- |
| `feat`     | 新功能    |
| `fix`      | Bug 修复  |
| `docs`     | 文档更新  |
| `refactor` | 重构      |
| `perf`     | 性能优化  |
| `test`     | 测试相关  |
| `chore`    | 构建/工具 |

### 示例

```
feat(alert): 添加 MITRE ATT&CK 映射

- 添加事件分类到 MITRE ATT&CK 技术映射
- 支持 T1566, T1204 等技术 ID

Closes #123
```

## PR 流程

### 1. Fork 项目

```bash
git clone https://github.com/YOUR_USERNAME/soc-copilot.git
cd soc-copilot
git remote add upstream https://github.com/ORIGINAL/soc-copilot.git
```

### 2. 创建分支

```bash
git checkout -b feature/alert-mitre-mapping
```

### 3. 提交 PR

1. 在 GitHub 上创建 Pull Request
2. 填写 PR 模板
3. 等待代码审查
4. 根据反馈修改
5. 合并后删除分支

## 安全测试要求

```bash
# 1. 依赖漏洞扫描
cd backend
safety check -r requirements.txt

cd frontend
npm audit

# 2. 静态分析
bandit -r .

# 3. 敏感信息检查
git log -p | grep -i "api_key\|password\|secret"
```

## 安全报告

如发现安全漏洞：

1. **不要**在公开 Issue 中报告
2. 发送邮件至 `security@soc-copilot.dev`

## 文档写作规范

````markdown
# 标题（必须使用 #）

## 适用对象（必须有）

描述文档的目标读者。

## 目标（必须有）

描述文档要解决的问题。

## 内容主体

使用二级标题（##）组织内容。

### 代码示例（必须有）

使用 ``` 包裹代码块。
````

## 社区资源

| 资源          | URL                                            |
| ------------- | ---------------------------------------------- |
| GitHub Issues | https://github.com/org/soc-copilot/issues      |
| 讨论区        | https://github.com/org/soc-copilot/discussions |
| Discord       | https://discord.gg/soc-copilot                 |

---

**文档版本**: v1.0  
**最后更新**: 2024-01-15
