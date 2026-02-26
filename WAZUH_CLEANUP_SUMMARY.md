# Wazuh 清理完成摘要

## ✅ 已完成

### 重命名的文件
- `frontend/components/wazuh/WazuhAlertStream.tsx` → `components/alerts/RealTimeAlertStream.tsx`
- `frontend/lib/wazuhWebSocket.ts` → `lib/alertWebSocket.ts`
- `frontend/types/wazuh.ts` → `types/alerts.ts`
- `backend/services/wazuh_stream_service.py` → `services/alert_stream_service.py`
- `backend/routers/wazuh_stream.py` → `routers/alert_stream.py`
- `backend/schemas/wazuh_stream.py` → `schemas/alert_stream.py`

### 删除的文件
- 所有 Wazuh 特定的路由、服务、模式文件
- 所有 Wazuh 配置和脚本
- Wazuh 页面目录

## 📝 需要手动修改

### 1. frontend/components/Navigation.tsx
```typescript
// 找到这一行：
{ label: "Wazuh", path: "/wazuh" }

// 改为：
{ label: "告警中心", path: "/alerts" }
```

### 2. backend/main.py
```python
// 删除这些导入（大约在第150-160行）：
from routers import wazuh_integration
from routers import wazuh_event_receiver
from services.wazuh_client import init_wazuh_client
from services.wazuh_log_receiver import init_wazuh_receiver

// 删除这些路由注册：
app.include_router(wazuh_integration.router)
app.include_router(wazuh_event_receiver.router)

// 删除 Wazuh 初始化代码块（大约50行，在startup事件中）

// 添加新的导入：
from routers import alert_stream

// 添加新的路由注册：
app.include_router(alert_stream.router)
```

### 3. 创建新页面
创建文件：`frontend/app/[locale]/alerts/page.tsx`

```typescript
'use client';

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useLocale } from 'next-intl';
import { loadAuthState, isAdmin } from "@/lib/auth";
import Navigation from "@/components/Navigation";
import { RealTimeAlertStream } from "@/components/alerts/RealTimeAlertStream";

export default function AlertsPage() {
  const router = useRouter();
  const locale = useLocale();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
    const authState = loadAuthState();
    if (!authState?.isAuthenticated) {
      router.push(`/${locale}/login`);
      return;
    }
  }, [router, locale]);

  if (!mounted) return null;

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <Navigation
        title="安全告警中心"
        subtitle="Real-time Alert Stream - Loki"
      />
      <main className="max-w-7xl mx-auto px-4 py-8">
        <RealTimeAlertStream
          maxAlerts={100}
          autoScroll={true}
          showFilters={true}
          dataSource="loki"
        />
      </main>
    </div>
  );
}
```

### 4. 更新 i18n 消息文件
在 `frontend/messages/zh.json` 和 `en.json` 中添加：

```json
{
  "alerts": {
    "title": "告警中心",
    "subtitle": "实时告警流"
  }
}
```

## 🧪 测试清单

- [ ] 前端启动正常
- [ ] 可以访问 /alerts 页面
- [ ] WebSocket 连接正常
- [ ] 后端启动无错误
- [ ] 可以接收到 Loki 告警
- [ ] 告警过滤功能正常
- [ ] 告警导出功能正常

## 🚀 下一步

1. 修改上述文件
2. 重启前端和后端服务
3. 测试所有功能
4. 提交更改：`git commit -m "refactor: migrate from Wazuh to Loki"`

