# Wazuh 清理 - 快速决策表

## 🎯 核心建议

### ✅ 保留并改造（3个高价值组件）

| 组件 | 当前位置 | 改造为 | 价值 |
|------|---------|--------|------|
| 实时告警流组件 | `frontend/components/wazuh/WazuhAlertStream.tsx` | `components/alerts/RealTimeAlertStream.tsx` | ⭐⭐⭐⭐⭐ |
| WebSocket客户端 | `frontend/lib/wazuhWebSocket.ts` | `lib/alertWebSocket.ts` | ⭐⭐⭐⭐ |
| 流服务架构 | `backend/services/wazuh_stream_service.py` | `services/alert_stream_service.py` | ⭐⭐⭐⭐ |

### ❌ 直接删除（Wazuh特定代码）

**后端（5个文件）**:
```bash
backend/routers/wazuh_integration.py
backend/routers/wazuh_event_receiver.py
backend/services/wazuh_client.py
backend/services/wazuh_alert_mapper.py
backend/services/wazuh_log_receiver.py
backend/schemas/wazuh.py
```

**配置（6个文件）**:
```bash
backend/.env.wazuh*
backend/docker-compose.wazuh.yml
backend/integrate_wazuh.sh
backend/setup_wazuh.sh
backend/test_wazuh_stream.sh
docker-compose.wazuh.yml
docker-compose.add-wazuh-api.yml
```

---

## 🔄 两步改造方案

### 步骤1：重命名通用组件

```bash
# 前端组件
mv frontend/components/wazuh/WazuhAlertStream.tsx \
   frontend/components/alerts/RealTimeAlertStream.tsx

mv frontend/lib/wazuhWebSocket.ts \
   frontend/lib/alertWebSocket.ts

mv frontend/types/wazuh.ts \
   frontend/types/alerts.ts

# 后端服务
mv backend/services/wazuh_stream_service.py \
   backend/services/alert_stream_service.py

mv backend/routers/wazuh_stream.py \
   backend/routers/alert_stream.py

mv backend/schemas/wazuh_stream.py \
   backend/schemas/alert_stream.py
```

### 步骤2：删除Wazuh特定代码

```bash
# 删除后端Wazuh集成
rm backend/routers/wazuh_integration.py
rm backend/routers/wazuh_event_receiver.py
rm backend/services/wazuh_client.py
rm backend/services/wazuh_alert_mapper.py
rm backend/services/wazuh_log_receiver.py
rm backend/schemas/wazuh.py

# 删除配置和脚本
rm backend/.env.wazuh*
rm backend/docker-compose.wazuh.yml
rm backend/integrate_wazuh.sh
rm backend/setup_wazuh.sh
rm backend/test_wazuh_stream.sh

# 删除根目录配置
rm docker-compose.wazuh.yml
rm docker-compose.add-wazuh-api.yml

# 删除Wazuh页面（将创建新的alerts页面）
rm -rf frontend/app/[locale]/wazuh/
```

---

## 📝 需要修改的文件

### 1. frontend/components/Navigation.tsx

```typescript
// 修改导航菜单
// 从：
{ label: "Wazuh", path: "/wazuh" }

// 改为：
{ label: "告警中心", path: "/alerts" }
```

### 2. backend/main.py

```python
# 删除这些导入：
from routers import wazuh_integration
from routers import wazuh_event_receiver
from routers import wazuh_stream
from services.wazuh_client import init_wazuh_client
from services.wazuh_log_receiver import init_wazuh_receiver

# 删除这些注册：
app.include_router(wazuh_integration.router)
app.include_router(wazuh_event_receiver.router)
app.include_router(wazuh_stream.router)

# 删除Wazuh初始化代码块（大约50行）

# 添加新的：
from routers import alert_stream
app.include_router(alert_stream.router)
```

### 3. 创建新页面

```typescript
// frontend/app/[locale]/alerts/page.tsx
'use client';

import { RealTimeAlertStream } from "@/components/alerts/RealTimeAlertStream";

export default function AlertsPage() {
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

---

## ⚡ 一键清理脚本

```bash
#!/bin/bash
# cleanup_wazuh.sh

echo "开始清理 Wazuh 相关代码..."

# 备份
git add -A
git commit -m "backup: before Wazuh cleanup"

# 重命名通用组件
echo "1. 重命名通用组件..."
mkdir -p frontend/components/alerts
mv frontend/components/wazuh/WazuhAlertStream.tsx frontend/components/alerts/RealTimeAlertStream.tsx
mv frontend/lib/wazuhWebSocket.ts frontend/lib/alertWebSocket.ts
mv frontend/types/wazuh.ts frontend/types/alerts.ts

# 删除Wazuh目录
rm -rf frontend/components/wazuh/

# 后端重命名
echo "2. 重命名后端组件..."
mv backend/services/wazuh_stream_service.py backend/services/alert_stream_service.py
mv backend/routers/wazuh_stream.py backend/routers/alert_stream.py
mv backend/schemas/wazuh_stream.py backend/schemas/alert_stream.py

# 删除Wazuh特定代码
echo "3. 删除Wazuh特定代码..."
rm backend/routers/wazuh_integration.py
rm backend/routers/wazuh_event_receiver.py
rm backend/services/wazuh_client.py
rm backend/services/wazuh_alert_mapper.py
rm backend/services/wazuh_log_receiver.py
rm backend/services/wazuh_event_receiver.py
rm backend/schemas/wazuh.py

# 删除配置
echo "4. 删除Wazuh配置..."
rm backend/.env.wazuh*
rm backend/docker-compose.wazuh.yml
rm backend/integrate_wazuh.sh
rm backend/setup_wazuh.sh
rm backend/test_wazuh_stream.sh
rm docker-compose.wazuh.yml
rm docker-compose.add-wazuh-api.yml

# 删除Wazuh页面
echo "5. 删除Wazuh页面..."
rm -rf frontend/app/[locale]/wazuh/

echo "✅ 清理完成！"
echo "请手动修改："
echo "  - frontend/components/Navigation.tsx"
echo "  - backend/main.py"
echo "  - 创建 frontend/app/[locale]/alerts/page.tsx"
```

---

## 📊 清理前后对比

| 项目 | 清理前 | 清理后 |
|------|--------|--------|
| 后端文件 | ~100KB Wazuh代码 | ~20KB 通用代码 |
| 前端组件 | 1个Wazuh专用页面 | 1个通用告警页面 |
| 依赖 | Wazuh API | Grafana + Loki |
| ARM64支持 | ❌ | ✅ |
| 维护成本 | 高 | 低 |

---

## 🎯 最终结果

### 保留的功能
- ✅ 实时告警流
- ✅ WebSocket 连接
- ✅ 告警过滤和统计
- ✅ 告警导出

### 新增功能
- ✅ Grafana 可视化
- ✅ Loki 日志查询
- ✅ 更强大的告警分析

### 删除的内容
- ❌ Wazuh API 集成
- ❌ Wazuh 特定依赖
- ❌ ARM64 不兼容的容器

---

**快速决策**: 保留3个通用组件，删除所有Wazuh特定代码，改造为Loki集成。
