# P1 功能实施计划

**实施日期**: 2026-02-25
**版本**: v0.9.0
**优先级**: P1 - 用户体验提升

---

## 📋 实施范围

### 1️⃣ 实时告警推送 (2-3天)
- WebSocket 连接管理
- 告警订阅和过滤
- 离线消息缓存

### 2️⃣ 告警列表页面 (3-4天)
- 实时告警流
- 高级过滤和搜索
- 批量操作
- 导出功能

### 3️⃣ 告警详情页面 (2-3天)
- 完整告警信息展示
- 威胁情报卡片
- MITRE ATT&CK 映射
- 关联告警视图
- 响应动作按钮

### 4️⃣ 威胁情报仪表盘 (3-4天)
- 告警趋势图表
- 威胁评分分布
- Top 攻击源 IP
- MITRE 战术热图
- IOC 统计

### 5️⃣ 告警生命周期管理 (2-3天)
- 状态流转
- 分配和升级
- 闭环工作流

### 6️⃣ AI 告警摘要 (2-3天)
- 自动摘要生成
- 多语言支持
- 摘要缓存

---

## 📂 文件结构

```
frontend/
├── app/
│   └── [locale]/
│       ├── alerts/
│       │   ├── page.tsx                    # 告警列表页
│       │   ├── [id]/
│       │   │   └── page.tsx                # 告警详情页
│       │   └── components/
│       │       ├── AlertList.tsx           # 告警列表组件
│       │       ├── AlertCard.tsx           # 告警卡片
│       │       ├── AlertFilters.tsx        # 过滤器
│       │       ├── AlertDetail.tsx         # 详情组件
│       │       ├── ThreatIntelCard.tsx     # 威胁情报卡片
│       │       ├── MITREMapping.tsx        # MITRE映射
│       │       ├── CorrelatedAlerts.tsx    # 关联告警
│       │       └── AlertActions.tsx        # 响应动作
│       ├── threat-intel/
│       │   └── dashboard/
│       │       └── page.tsx                # 威胁情报仪表盘
│       │       └── components/
│       │           ├── TrendsChart.tsx     # 趋势图
│       │           ├── SeverityDist.tsx    # 严重程度分布
│       │           ├── TopSources.tsx      # Top攻击源
│       │           ├── MITREHeatmap.tsx    # MITRE热图
│       │           └── IOCStats.tsx        # IOC统计
│       └── components/
│           ├── AlertWebSocket.tsx          # WebSocket组件
│           ├── AlertStatusBadge.tsx        # 状态徽章
│           ├── SeverityIndicator.tsx       # 严重程度指示器
│           └── TimelineView.tsx            # 时间线视图

backend/
├── routers/
│   ├── websocket.py                        # WebSocket路由
│   └── alerts_lifecycle.py                 # 告警生命周期API
├── services/
│   ├── alert_subscription.py               # 订阅服务
│   ├── alert_summary.py                    # AI摘要服务
│   ├── alert_lifecycle.py                  # 生命周期服务
│   └── offline_cache.py                    # 离线缓存
└── schemas/
    └── alert_lifecycle.py                  # 生命周期Schema
```

---

## 🚀 实施顺序

### Phase 1: WebSocket 实时推送 (Day 1-2)
- [ ] WebSocket 连接管理
- [ ] 告警广播
- [ ] 订阅管理
- [ ] 离线消息缓存

### Phase 2: 告警列表页面 (Day 3-6)
- [ ] 列表组件
- [ ] 过滤器
- [ ] 批量操作
- [ ] 实时更新

### Phase 3: 告警详情页面 (Day 7-9)
- [ ] 详情布局
- [ ] 威胁情报展示
- [ ] MITRE映射
- [ ] 关联分析

### Phase 4: 威胁情报仪表盘 (Day 10-13)
- [ ] 统计API
- [ ] 图表组件
- [ ] 实时数据

### Phase 5: 生命周期管理 (Day 14-16)
- [ ] 状态API
- [ ] 分配功能
- [ ] 升级规则
- [ ] 工作流

### Phase 6: AI 摘要 (Day 17-19)
- [ ] 摘要生成
- [ ] 缓存机制
- [ ] 多语言

---

## 🎯 今天开始: Phase 1 - WebSocket 实时推送

### 实施内容
1. 后端 WebSocket 路由
2. 前端 WebSocket 组件
3. 订阅管理服务
4. 离线缓存机制

---

## 📊 API 设计

### WebSocket
```
WS /api/v1/ws/alerts
- 连接时需要认证
- 支持订阅过滤（严重程度、事件类型）
- 心跳检测
```

### REST API
```
POST   /api/v1/alerts/{id}/assign          # 分配告警
POST   /api/v1/alerts/{id}/escalate        # 升级告警
POST   /api/v1/alerts/{id}/resolve         # 解决告警
POST   /api/v1/alerts/{id}/summary         # 生成AI摘要
GET    /api/v1/alerts/statistics/trends    # 趋势统计
GET    /api/v1/alerts/statistics/sources   # 攻击源统计
```

---

开始实施？
