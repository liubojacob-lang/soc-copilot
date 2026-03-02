# Wazuh 相关代码清理分析报告

## 📋 执行摘要

**背景**: 由于 Wazuh 官方镜像不支持 ARM64 架构，SOC Copilot 项目已采用 **Grafana + Loki** 作为替代方案。

**目的**: 分析所有 Wazuh 相关代码，确定哪些应该保留（通用组件），哪些应该删除（Wazuh 特定代码）。

---

## 🔍 详细文件清单

### 1. 前端文件 (Frontend)

| 文件路径 | 类型 | 大小 | 说明 | 建议 |
|---------|------|------|------|------|
| `frontend/app/[locale]/wazuh/page.tsx` | 页面 | 2.2KB | Wazuh 告警流页面 | **可以改造复用** |
| `frontend/components/wazuh/WazuhAlertStream.tsx` | 组件 | 17KB | 实时告警流组件 | **建议保留并改造** |
| `frontend/types/wazuh.ts` | 类型定义 | - | Wazuh 数据类型 | **建议改造为通用类型** |
| `frontend/lib/wazuhWebSocket.ts` | WebSocket库 | - | WebSocket 客户端 | **建议改造为通用客户端** |

### 2. 后端路由 (Backend Routers)

| 文件路径 | 类型 | 大小 | 说明 | 建议 |
|---------|------|------|------|------|
| `backend/routers/wazuh_integration.py` | 路由 | 15KB | Wazuh API 集成 | ❌ **删除** |
| `backend/routers/wazuh_stream.py` | 路由 | 11KB | Wazuh 实时流 | ⚠️ **改造复用** |
| `backend/routers/wazuh_event_receiver.py` | 路由 | 1.2KB | Webhook 接收器 | ❌ **删除** |

### 3. 后端服务 (Backend Services)

| 文件路径 | 类型 | 大小 | 说明 | 建议 |
|---------|------|------|------|------|
| `backend/services/wazuh_alert_mapper.py` | 服务 | 20KB | 告警映射器 | ❌ **删除** |
| `backend/services/wazuh_client.py` | 服务 | 16KB | Wazuh API 客户端 | ❌ **删除** |
| `backend/services/wazuh_event_receiver.py` | 服务 | 2.0KB | 事件接收服务 | ❌ **删除** |
| `backend/services/wazuh_log_receiver.py` | 服务 | 12KB | 日志接收器 | ❌ **删除** |
| `backend/services/wazuh_stream_service.py` | 服务 | 14KB | 实时流服务 | ⚠️ **改造复用** |

### 4. 后端模式 (Backend Schemas)

| 文件路径 | 类型 | 大小 | 说明 | 建议 |
|---------|------|------|------|------|
| `backend/schemas/wazuh.py` | Schema | - | Wazuh 数据模式 | ❌ **删除** |
| `backend/schemas/wazuh_stream.py` | Schema | - | 流数据模式 | ⚠️ **改造为通用模式** |

### 5. 配置文件 (Config Files)

| 文件路径 | 类型 | 说明 | 建议 |
|---------|------|------|------|
| `backend/.env.wazuh` | 环境变量 | Wazuh 配置 | ❌ **删除** |
| `backend/.env.wazuh.example` | 环境变量模板 | 配置模板 | ❌ **删除** |
| `backend/docker-compose.wazuh.yml` | Docker Compose | Wazuh 容器配置 | ❌ **删除** |
| `backend/integrate_wazuh.sh` | 脚本 | Wazuh 集成脚本 | ❌ **删除** |
| `backend/setup_wazuh.sh` | 脚本 | Wazuh 安装脚本 | ❌ **删除** |
| `backend/test_wazuh_stream.sh` | 脚本 | 测试脚本 | ❌ **删除** |

### 6. 根目录配置 (Root Config)

| 文件路径 | 说明 | 建议 |
|---------|------|------|
| `docker-compose.wazuh.yml` | Wazuh 容器编排 | ❌ **删除** |
| `docker-compose.add-wazuh-api.yml` | Wazuh API 配置 | ❌ **删除** |
| `docker-compose.security.yml` | 安全配置（含 Wazuh） | ⚠️ **检查后删除** |

---

## 🎯 保留与改造建议

### ✅ 建议保留并改造

#### 1. **实时告警流组件** (高价值)

**文件**: `frontend/components/wazuh/WazuhAlertStream.tsx`

**保留理由**:
- 完整的 WebSocket 实时告警展示组件
- 包含过滤、统计、导出等功能
- UI 设计优秀，可复用性强

**改造方案**:
```typescript
// 改造为通用组件
// frontend/components/alerts/RealTimeAlertStream.tsx

interface AlertData {
  id: string;
  timestamp: string;
  severity: 'critical' | 'high' | 'medium' | 'low' | 'info';
  title: string;
  source: string;  // 从 Wazuh agent 改为通用源
  full_log: string;
  iocs: string[];
  metadata: Record<string, any>;  // 通用元数据
}

// 数据源改造
// - 从 Wazuh WebSocket 改为 Loki/SSE
// - 或使用通用 WebSocket 接口
```

#### 2. **WebSocket 客户端库**

**文件**: `frontend/lib/wazuhWebSocket.ts`

**保留理由**:
- 完整的 WebSocket 连接管理
- 自动重连机制
- 错误处理完善

**改造方案**:
```typescript
// 改造为通用客户端
// frontend/lib/alertWebSocket.ts

interface AlertWebSocketConfig {
  url: string;  // 可配置的 URL
  token: string;
  enableAggregation: boolean;
}

// 支持多种数据源
// - Wazuh WebSocket
// - 自定义 WebSocket
// - Server-Sent Events (SSE)
```

#### 3. **后端实时流服务架构**

**文件**: `backend/services/wazuh_stream_service.py`

**保留理由**:
- 完整的流数据处理架构
- 告警聚合逻辑
- 连接管理机制

**改造方案**:
```python
# 改造为通用流服务
# backend/services/alert_stream_service.py

class AlertStreamService:
    """通用告警流服务"""

    async def push_alert(self, alert: AlertData):
        """推送新告警到流"""

    async def get_aggregated_alerts(self):
        """获取聚合后的告警"""

    async def broadcast_to_clients(self):
        """广播到所有连接的客户端"""
```

### ❌ 建议删除

#### 1. Wazuh 特定集成代码

**文件列表**:
- `backend/routers/wazuh_integration.py`
- `backend/services/wazuh_client.py`
- `backend/services/wazuh_alert_mapper.py`
- `backend/services/wazuh_log_receiver.py`
- `backend/schemas/wazuh.py`

**删除理由**:
- 完全依赖 Wazuh API
- 无法用于其他数据源
- 维护成本高

#### 2. Wazuh 容器和脚本

**文件列表**:
- `docker-compose.wazuh.yml`
- `docker-compose.add-wazuh-api.yml`
- `backend/integrate_wazuh.sh`
- `backend/setup_wazuh.sh`
- `backend/test_wazuh_stream.sh`

**删除理由**:
- Wazuh 在 ARM64 上无法运行
- 已被 Grafana + Loki 替代

#### 3. 环境配置

**文件列表**:
- `backend/.env.wazuh`
- `backend/.env.wazuh.example`

**删除理由**:
- 包含 Wazuh 特定配置
- 不再需要

---

## 🔄 迁移方案

### 方案 A: 完全删除 Wazuh，使用 Loki

#### 前端改造

1. **删除 Wazuh 页面**
```bash
rm frontend/app/[locale]/wazuh/page.tsx
```

2. **改造告警流组件**
```bash
# 重命名并改造
mv frontend/components/wazuh/WazuhAlertStream.tsx \
   frontend/components/alerts/LokiAlertStream.tsx

# 修改数据源为 Loki API
```

3. **创建新页面**
```typescript
// frontend/app/[locale]/alerts/page.tsx
import { LokiAlertStream } from "@/components/alerts/LokiAlertStream";

export default function AlertsPage() {
  return (
    <div>
      <h1>安全告警中心</h1>
      <LokiAlertStream dataSource="loki" />
    </div>
  );
}
```

#### 后端改造

1. **删除 Wazuh 路由和服务**
```bash
# 删除 Wazuh 路由
rm backend/routers/wazuh_*.py

# 删除 Wazuh 服务
rm backend/services/wazuh_*.py

# 删除 Wazuh 模式
rm backend/schemas/wazuh*.py
```

2. **创建 Loki 集成路由**
```python
# backend/routers/loki_alerts.py
from services.loki_alert_sender import get_loki_sender

@router.get("/api/v1/alerts/stream")
async def stream_alerts():
    """从 Loki 获取告警流"""

@router.post("/api/v1/alerts/send")
async def send_alert(alert: AlertData):
    """发送告警到 Loki"""
```

3. **修改 main.py**
```python
# 删除 Wazuh 路由注册
# - wazuh_integration
# - wazuh_event_receiver
# - wazuh_stream

# 添加 Loki 路由
from routers import loki_alerts
app.include_router(loki_alerts.router)

# 删除 Wazuh 初始化代码
```

### 方案 B: 保留架构，改造为通用方案

#### 创建通用告警流架构

1. **通用数据类型**
```typescript
// frontend/types/alerts.ts
export interface AlertData {
  id: string;
  timestamp: string;
  severity: SeverityLevel;
  title: string;
  description: string;
  source: AlertSource;
  iocs: string[];
  metadata: Record<string, any>;
}

export interface AlertSource {
  type: 'wazuh' | 'loki' | 'custom';
  name: string;
  ip: string;
}
```

2. **通用 WebSocket 客户端**
```typescript
// frontend/lib/alertWebSocket.ts
export class AlertWebSocketClient {
  constructor(config: AlertWebSocketConfig) {}

  connect(): void {}
  disconnect(): void {}
  onAlert(callback: (alert: AlertData) => void): UnsubscribeFunction {}
  // ... 通用方法
}
```

3. **后端通用流服务**
```python
# backend/services/alert_stream_service.py
class AlertStreamService:
    """通用告警流服务，支持多数据源"""

    async def push_alert(self, alert: AlertData):
        """从任何数据源接收告警"""

    async def get_aggregated_alerts(self):
        """获取聚合告警"""
```

---

## 📊 清理清单

### 立即删除（Wazuh 特定）

```bash
# 后端路由
rm backend/routers/wazuh_integration.py
rm backend/routers/wazuh_event_receiver.py

# 后端服务（保留 wazuh_stream_service.py 用于改造）
rm backend/services/wazuh_client.py
rm backend/services/wazuh_alert_mapper.py
rm backend/services/wazuh_log_receiver.py
rm backend/services/wazuh_event_receiver.py

# 后端模式
rm backend/schemas/wazuh.py

# 配置文件
rm backend/.env.wazuh
rm backend/.env.wazuh.example
rm backend/docker-compose.wazuh.yml
rm backend/integrate_wazuh.sh
rm backend/setup_wazuh.sh
rm backend/test_wazuh_stream.sh

# 根目录配置
rm docker-compose.wazuh.yml
rm docker-compose.add-wazuh-api.yml
```

### 保留并改造（通用组件）

```bash
# 前端组件
mv frontend/components/wazuh/WazuhAlertStream.tsx \
   frontend/components/alerts/RealTimeAlertStream.tsx

# WebSocket 客户端
mv frontend/lib/wazuhWebSocket.ts \
   frontend/lib/alertWebSocket.ts

# 类型定义
mv frontend/types/wazuh.ts \
   frontend/types/alerts.ts

# 后端流服务
mv backend/services/wazuh_stream_service.py \
   backend/services/alert_stream_service.py

# 后端流路由
mv backend/routers/wazuh_stream.py \
   backend/routers/alert_stream.py

# 后端流模式
mv backend/schemas/wazuh_stream.py \
   backend/schemas/alert_stream.py
```

### 修改主文件

**frontend/app/[locale]/wazuh/page.tsx**
```typescript
// 改造为通用告警页面
// frontend/app/[locale]/alerts/page.tsx
import { RealTimeAlertStream } from "@/components/alerts/RealTimeAlertStream";

export default function AlertsPage() {
  return <RealTimeAlertStream dataSource="loki" />;
}
```

**frontend/components/Navigation.tsx**
```typescript
// 修改导航菜单
{ label: "告警中心", path: "/alerts" }  // 从 Wazuh 改为告警中心
```

**backend/main.py**
```python
# 删除 Wazuh 导入和初始化
# - from routers import wazuh_integration
# - from routers import wazuh_event_receiver
# - from services.wazuh_client import init_wazuh_client
# - ...

# 添加通用告警流
from routers import alert_stream
from services.alert_stream_service import init_alert_stream_service

app.include_router(alert_stream.router)
```

---

## 🎯 推荐方案

### 最佳实践：混合方案

1. **保留优秀的架构和组件**
   - ✅ 前端实时告警流组件（改造为通用）
   - ✅ WebSocket 客户端库（改造为通用）
   - ✅ 后端流服务架构（改造为通用）

2. **删除 Wazuh 特定代码**
   - ❌ Wazuh API 客户端
   - ❌ Wazuh 告警映射器
   - ❌ Wazuh 日志接收器
   - ❌ 所有 Wazuh 容器和脚本

3. **创建新的 Loki 集成**
   - ✅ Loki API 客户端
   - ✅ Loki 告警流路由
   - ✅ Loki 数据模式

4. **更新 UI 和导航**
   - 将 "Wazuh" 改为 "告警中心" 或 "安全监控"
   - 支持多数据源（Loki 作为主数据源）
   - 保留实时流功能

---

## 📝 后续步骤

### 第 1 步：备份现有代码
```bash
git add -A
git commit -m "backup: Wazuh integration before cleanup"
```

### 第 2 步：删除 Wazuh 特定代码
```bash
# 执行清理清单中的删除命令
```

### 第 3 步：改造通用组件
```bash
# 重命名并改造组件
```

### 第 4 步：创建 Loki 集成
```bash
# 添加 Loki API 集成代码
```

### 第 5 步：更新导航和路由
```bash
# 修改菜单和页面链接
```

### 第 6 步：测试
```bash
# 启动服务
# 测试告警流功能
# 验证所有功能正常
```

---

## ⚠️ 注意事项

### 依赖检查

在删除之前，确保：

1. **没有其他代码依赖 Wazuh 模块**
```bash
grep -r "wazuh" backend/ frontend/ --exclude-dir=node_modules
```

2. **导航菜单已更新**
```bash
# 更新 frontend/components/Navigation.tsx
```

3. **路由配置已修改**
```bash
# 更新路由注册
```

### 数据迁移

如果有历史 Wazuh 数据需要保留：

1. **导出 Wazuh 告警数据**
2. **转换为 Loki 格式**
3. **导入到 Loki**

---

## 📈 影响评估

### 代码量减少

- **前端**: ~2 个文件，~20KB 代码
- **后端**: ~8 个文件，~100KB 代码
- **配置**: ~6 个文件
- **总计**: ~16 个文件，~120KB 代码

### 维护成本降低

- ❌ 不再维护 Wazuh 特定代码
- ❌ 不需要处理 ARM64 兼容性
- ✅ 使用标准 Grafana + Loki 方案
- ✅ 社区支持更好

### 功能增强

- ✅ 更强大的可视化（Grafana）
- ✅ 更灵活的查询（LogQL）
- ✅ 更好的性能
- ✅ ARM64 原生支持

---

**报告生成时间**: 2026-02-26
**分析状态**: ✅ 完成
