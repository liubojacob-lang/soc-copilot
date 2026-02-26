# 前端说明

## 适用对象

前端开发人员、需要修改/扩展界面的工程师。

## 目标

理解前端架构、页面结构、常见问题排查。

## 页面结构

```
frontend/app/
├── page.tsx                    # 首页 - 告警分析仪表盘
├── login/
│   └── page.tsx               # 登录页
├── ai-assistant/
│   └── page.tsx               # AI 对话助手
├── alerts/
│   └── page.tsx               # 告警列表
├── assets/
│   └── page.tsx               # 资产管理
├── playbooks/
│   ├── page.tsx               # 剧本列表
│   └── [id]/
│       └── page.tsx           # 剧本编辑器
├── triggers/
│   └── page.tsx               # 触发器管理
└── settings/
    └── page.tsx               # 系统设置
```

## API 调用层

所有前端 API 调用通过 `lib/api.ts`：

```typescript
import { api } from "@/lib/api";

export async function analyzeAlert(rawLog: string) {
  return api.post("/api/ai/analyze-alert", { raw_log: rawLog });
}

export async function executePlaybook(id: string, mode: "dry_run" | "run") {
  return api.post(`/api/playbook-definitions/${id}/run`, { mode });
}
```

## DAG 编辑器

使用 React Flow 实现：

```tsx
import ReactFlow from 'reactflow';

export function DAGEditor({ definition, onSave }) {
  const [nodes, setNodes] = useNodesState(definition.nodes);
  const [edges, setEdges] = useEdgesState(definition.edges);
  
  return (
    <div style={{ height: 500 }}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onConnect={(params) => setEdges((eds) => addEdge(params, eds))}
      />
    </div>
  );
}
```

## 常见坑与排查

### 1. Maximum update depth exceeded

**原因**：React 状态更新导致无限循环

**解决**：使用 useCallback 包装回调

```tsx
const handleSubmit = useCallback(async () => {
  await api.post("/submit", { data });
}, [data]);
```

### 2. API 请求重复发送

**解决**：使用 AbortController

```tsx
useEffect(() => {
  const controller = new AbortController();
  const fetch = async () => {
    const data = await api.get("/data", { signal: controller.signal });
    setData(data);
  };
  fetch();
  return () => controller.abort();
}, [dependency]);
```

### 3. 状态丢失

**解决**：使用 Zustand 管理全局状态

```typescript
import { create } from 'zustand';

interface AlertStore {
  selectedAlert: Alert | null;
  setAlert: (alert: Alert) => void;
}

export const useAlertStore = create<AlertStore>((set) => ({
  selectedAlert: null,
  setAlert: (alert) => set({ selected}));
```

## Alert: alert }),
样式规范

使用 Tailwind CSS：

```tsx
// ✅ 正确
<div className="flex items-center gap-4 p-4 bg-white rounded-lg shadow">
  <span className="text-gray-600">状态:</span>
  <Badge variant="success">已处理</Badge>
</div>
```
