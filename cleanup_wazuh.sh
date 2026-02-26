#!/bin/bash
#
# Wazuh 清理脚本
# 将 Wazuh 集成改造为通用的 Loki + Grafana 方案
#

set -e

echo "=================================================="
echo "  SOC Copilot - Wazuh 清理脚本"
echo "=================================================="
echo ""

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 步骤 1: 备份当前代码
echo -e "${YELLOW}步骤 1/6: 备份当前代码${NC}"
git add -A 2>/dev/null || echo "  ⚠️  Git 仓库未初始化，跳过备份"
git commit -m "backup: before Wazuh cleanup" 2>/dev/null || echo "  ⚠️  无法创建备份"
echo "  ✅ 备份完成"
echo ""

# 步骤 2: 重命名通用组件
echo -e "${YELLOW}步骤 2/6: 重命名通用组件${NC}"

# 创建必要的目录
mkdir -p frontend/components/alerts
mkdir -p frontend/components/monitor

# 前端组件
if [ -f "frontend/components/wazuh/WazuhAlertStream.tsx" ]; then
    mv frontend/components/wazuh/WazuhAlertStream.tsx \
       frontend/components/alerts/RealTimeAlertStream.tsx
    echo "  ✅ WazuhAlertStream → RealTimeAlertStream"
fi

if [ -f "frontend/lib/wazuhWebSocket.ts" ]; then
    mv frontend/lib/wazuhWebSocket.ts \
       frontend/lib/alertWebSocket.ts
    echo "  ✅ wazuhWebSocket → alertWebSocket"
fi

if [ -f "frontend/types/wazuh.ts" ]; then
    mv frontend/types/wazuh.ts \
       frontend/types/alerts.ts
    echo "  ✅ wazuh.ts → alerts.ts"
fi

# 后端组件
if [ -f "backend/services/wazuh_stream_service.py" ]; then
    mv backend/services/wazuh_stream_service.py \
       backend/services/alert_stream_service.py
    echo "  ✅ wazuh_stream_service → alert_stream_service"
fi

if [ -f "backend/routers/wazuh_stream.py" ]; then
    mv backend/routers/wazuh_stream.py \
       backend/routers/alert_stream.py
    echo "  ✅ wazuh_stream router → alert_stream router"
fi

if [ -f "backend/schemas/wazuh_stream.py" ]; then
    mv backend/schemas/wazuh_stream.py \
       backend/schemas/alert_stream.py
    echo "  ✅ wazuh_stream schema → alert_stream schema"
fi

# 删除空的 wazuh 目录
if [ -d "frontend/components/wazuh" ]; then
    rm -rf frontend/components/wazuh
    echo "  ✅ 删除 frontend/components/wazuh/"
fi

echo ""

# 步骤 3: 删除 Wazuh 特定代码
echo -e "${YELLOW}步骤 3/6: 删除 Wazuh 特定代码${NC}"

# 后端路由
for file in backend/routers/wazuh_integration.py \
            backend/routers/wazuh_event_receiver.py; do
    if [ -f "$file" ]; then
        rm "$file"
        echo "  ✅ 删除 $file"
    fi
done

# 后端服务
for file in backend/services/wazuh_client.py \
            backend/services/wazuh_alert_mapper.py \
            backend/services/wazuh_log_receiver.py \
            backend/services/wazuh_event_receiver.py; do
    if [ -f "$file" ]; then
        rm "$file"
        echo "  ✅ 删除 $file"
    fi
done

# 后端模式
for file in backend/schemas/wazuh.py; do
    if [ -f "$file" ]; then
        rm "$file"
        echo "  ✅ 删除 $file"
    fi
done

echo ""

# 步骤 4: 删除配置和脚本
echo -e "${YELLOW}步骤 4/6: 删除配置和脚本${NC}"

# 环境配置
for file in backend/.env.wazuh \
            backend/.env.wazuh.example; do
    if [ -f "$file" ]; then
        rm "$file"
        echo "  ✅ 删除 $file"
    fi
done

# Docker 配置
for file in backend/docker-compose.wazuh.yml \
            docker-compose.wazuh.yml \
            docker-compose.add-wazuh-api.yml; do
    if [ -f "$file" ]; then
        rm "$file"
        echo "  ✅ 删除 $file"
    fi
done

# 脚本
for file in backend/integrate_wazuh.sh \
            backend/setup_wazuh.sh \
            backend/test_wazuh_stream.sh; do
    if [ -f "$file" ]; then
        rm "$file"
        echo "  ✅ 删除 $file"
    fi
done

echo ""

# 步骤 5: 删除 Wazuh 页面
echo -e "${YELLOW}步骤 5/6: 删除 Wazuh 页面${NC}"

if [ -d "frontend/app/[locale]/wazuh" ]; then
    rm -rf frontend/app/[locale]/wazuh
    echo "  ✅ 删除 frontend/app/[locale]/wazuh/"
fi

echo ""

# 步骤 6: 创建迁移摘要
echo -e "${YELLOW}步骤 6/6: 生成迁移摘要${NC}"

cat > WAZUH_CLEANUP_SUMMARY.md << 'EOF'
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

EOF

echo "  ✅ 创建 WAZUH_CLEANUP_SUMMARY.md"

echo ""
echo "=================================================="
echo -e "${GREEN}✅ Wazuh 清理完成！${NC}"
echo "=================================================="
echo ""
echo "📋 后续步骤："
echo "  1. 查看 WAZUH_CLEANUP_SUMMARY.md 了解需要手动修改的文件"
echo "  2. 修改 Navigation.tsx 和 main.py"
echo "  3. 创建新的 alerts 页面"
echo "  4. 重启服务并测试"
echo ""
echo "📄 详细分析报告："
echo "  - WAZUH_CLEANUP_ANALYSIS.md (完整分析)"
echo "  - WAZUH_CLEANUP_QUICK_REF.md (快速参考)"
echo ""
