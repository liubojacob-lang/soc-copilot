# 前端代码分割优化指南

**更新时间**: 2026-03-02

---

## 🎯 优化目标

减少首屏加载时间 40-60%，提升用户体验。

---

## 📋 当前问题分析

### 大型组件（需要优化）

```typescript
// 以下组件超过 400 行，应该使用代码分割
components/ChatHistorySidebar.tsx         672 行
components/alerts/RealTimeAlertStream.tsx  543 行
components/Navigation.tsx                  484 行
components/websocket/FilterConfig.tsx      477 行
components/tabs/AssetsTab.tsx              460 行
components/dag/DAGCanvas.tsx               422 行
components/common/Input.tsx                410 行
components/websocket/MonitoringDashboard.tsx 386 行
components/monitor/IOCStats.tsx            384 行
```

---

## ✅ 优化方案

### 1. 使用 Next.js 动态导入

#### Before（静态导入）

```typescript
import { HeavyComponent } from './HeavyComponent'
import { LargeChart } from './LargeChart'

export default function Page() {
  return (
    <div>
      <HeavyComponent />
      <LargeChart />
    </div>
  )
}
```

#### After（动态导入）

```typescript
'use client'

import dynamic from 'next/dynamic'
import { Skeleton } from './components/common/Skeleton'

// 动态导入大型组件
const HeavyComponent = dynamic(
  () => import('./HeavyComponent'),
  {
    loading: () => <Skeleton className="w-full h-64" />,
    ssr: false,  // 仅客户端渲染（可选）
  }
)

const LargeChart = dynamic(
  () => import('./LargeChart'),
  {
    loading: () => <Skeleton className="w-full h-96" />,
  }
)

export default function Page() {
  return (
    <div>
      <HeavyComponent />
      <LargeChart />
    </div>
  )
}
```

---

### 2. 路由级代码分割（Next.js 自动支持）

Next.js 已经自动为每个路由页面进行代码分割。无需额外配置。

```typescript
// app/[locale]/audit/page.tsx
// Next.js 自动创建独立的 chunk
export default function AuditPage() {
  return <div>Audit Logs</div>
}
```

---

### 3. 条件加载组件

对于仅在特定条件下显示的组件，使用动态导入：

```typescript
'use client'

import dynamic from 'next/dynamic'
import { useState } from 'react'

const AdminPanel = dynamic(
  () => import('./AdminPanel'),
  {
    loading: () => <div>Loading admin panel...</div>
  }
)

export default function Dashboard({ user }) {
  const [showAdmin, setShowAdmin] = useState(false)

  return (
    <div>
      <h1>Dashboard</h1>

      {/* 仅在需要时加载 AdminPanel */}
      {showAdmin && user.isAdmin && (
        <AdminPanel />
      )}
    </div>
  )
}
```

---

### 4. 特定优化示例

#### 示例 1: 优化 ChatHistorySidebar

```typescript
// components/ChatHistorySidebar.tsx (672 行)
// 改为动态导入

'use client'

import dynamic from 'next/dynamic'
import { Skeleton } from './common/Skeleton'

const ChatHistorySidebar = dynamic(
  () => import('./ChatHistorySidebar'),
  {
    loading: () => (
      <div className="w-64 border-r p-4">
        <Skeleton className="h-6 w-3/4 mb-4" />
        <Skeleton className="h-4 w-full mb-2" />
        <Skeleton className="h-4 w-5/6 mb-2" />
        <Skeleton className="h-4 w-4/6" />
      </div>
    ),
  }
)

export default function ChatPage() {
  return (
    <div className="flex h-screen">
      <ChatHistorySidebar />
      {/* 其他内容 */}
    </div>
  )
}
```

#### 示例 2: 优化 RealTimeAlertStream

```typescript
// components/alerts/RealTimeAlertStream.tsx (543 行)

'use client'

import dynamic from 'next/dynamic'
import { Skeleton } from '../common/Skeleton'

const RealTimeAlertStream = dynamic(
  () => import('./alerts/RealTimeAlertStream'),
  {
    loading: () => (
      <div className="p-4 space-y-3">
        <Skeleton className="h-20 w-full" />
        <Skeleton className="h-20 w-full" />
        <Skeleton className="h-20 w-full" />
      </div>
    ),
    ssr: false,  // WebSocket 组件不需要 SSR
  }
)

export default function AlertsPage() {
  return (
    <div>
      <RealTimeAlertStream />
    </div>
  )
}
```

#### 示例 3: 优化 DAGCanvas

```typescript
// components/dag/DAGCanvas.tsx (422 行)

'use client'

import dynamic from 'next/dynamic'
import { Skeleton } from '../common/Skeleton'

const DAGCanvas = dynamic(
  () => import('./dag/DAGCanvas'),
  {
    loading: () => (
      <div className="w-full h-[600px] flex items-center justify-center">
        <div className="text-center">
          <div className="animate-pulse">
            <Skeleton className="h-[600px] w-full" />
          </div>
          <p className="text-gray-500 mt-4">Loading workflow editor...</p>
        </div>
      </div>
    ),
  }
)

export default function PlaybookEditorPage() {
  return (
    <div>
      <DAGCanvas />
    </div>
  )
}
```

---

### 5. 预加载策略

对于关键路径的组件，可以添加预加载：

```typescript
import dynamic from 'next/dynamic'
import { useRouter } from 'next/navigation'

export default function Navigation() {
  const router = useRouter()

  // 预加载用户可能访问的页面
  const handleMouseEnter = (path: string) => {
    router.prefetch(path)
  }

  return (
    <nav>
      <a
        href="/alerts"
        onMouseEnter={() => handleMouseEnter('/alerts')}
      >
        Alerts
      </a>
    </nav>
  )
}
```

---

### 6. Web Vitals 监控

使用已添加的 Web Vitals 组件监控性能：

```typescript
// app/layout.tsx
import { WebVitals } from '@/components/WebVitals'

export default function RootLayout({ children }) {
  return (
    <html>
      <body>
        <WebVitals />
        {children}
      </body>
    </html>
  )
}
```

---

## 📊 预期效果

### 优化前

```
首屏加载: 3-5 秒
包大小: 2-3 MB
Time to Interactive: 4-6 秒
```

### 优化后

```
首屏加载: 1-2 秒 (↓ 60%)
包大小: 800KB-1.2MB (↓ 50-60%)
Time to Interactive: 2-3 秒 (↓ 50%)
```

---

## 🎯 实施优先级

### 高优先级（立即实施）

1. **ChatHistorySidebar** (672行) - 最重的组件
2. **RealTimeAlertStream** (543行) - WebSocket 组件
3. **Navigation** (484行) - 每个页面都使用

### 中优先级（本周完成）

4. **DAGCanvas** (422行) - 仅编辑器页面
5. **AssetsTab** (460行) - 仅资产页面
6. **IOCStats** (384行) - 仅监控页面

### 低优先级（择机完成）

7. **FilterConfig** (477行) - 仅配置页面
8. **Input** (410行) - 通用组件（已优化）

---

## ✅ 验证方法

### 1. Chrome DevTools 检查

```
1. 打开 Chrome DevTools (F12)
2. 切换到 Network 标签
3. 勾选 "Disable cache"
4. 刷新页面
5. 查看 .js 文件大小和数量
```

### 2. Lighthouse 评分

```
1. 打开 Chrome DevTools
2. 切换到 Lighthouse 标签
3. 选择 "Performance"
4. 点击 "Analyze page load"
5. 查看 Performance 分数（目标: 90+）
```

### 3. Next.js 内置分析

```bash
cd frontend
npm run build

# 查看输出报告
# ✅ First Load JS shared by all 64 KB
# ✅ Page / 97 kB
```

---

## 📝 实施检查清单

### Phase 1: 核心组件（1小时）

- [ ] ChatHistorySidebar 动态导入
- [ ] RealTimeAlertStream 动态导入
- [ ] Navigation 动态导入

### Phase 2: 页面级组件（1小时）

- [ ] DAGCanvas 动态导入
- [ ] AssetsTab 动态导入
- [ ] IOCStats 动态导入

### Phase 3: 其他优化（30分钟）

- [ ] 添加预加载
- [ ] Web Vitals 监控
- [ ] 性能测试

---

## 🔗 参考资源

- [Next.js Dynamic Imports](https://nextjs.org/docs/advanced-features/dynamic-import)
- [Code Splitting](https://webpack.js.org/guides/code-splitting/)
- [Web Vitals](https://web.dev/vitals/)

---

**准备开始优化了吗？选择一个组件开始吧！** 🚀
