# Week 2: WebSocket 实时推送完善计划

**日期**: 2026-02-25
**选项**: A - 完善 WebSocket 实时推送
**预计时间**: 4 天

---

## 📊 Week 1 完成情况

### ✅ 已完成

- [x] 后端流服务 (HTTP API)
- [x] 后端 WebSocket 服务器 (已有完整实现)
- [x] 前端告警流页面 (HTTP 轮询版本)
- [x] 数据模型完整
- [x] 基本测试通过

### ⏳ 待完善

- [ ] 前端 WebSocket 客户端集成
- [ ] 实时统计自动更新
- [ ] 告警列表实时追加
- [ ] 连接状态指示器优化
- [ ] 自动重连机制

---

## 🎯 Week 2 任务清单

### Day 1: 后端 WebSocket 测试和验证

**目标**: 验证后端 WebSocket 功能完全正常

**任务**:

- [ ] 1.1 测试 WebSocket 连接
  - [ ] 使用 wscat 或 websocat 测试连接
  - [ ] 验证 token 认证
  - [ ] 测试 ping/pong 心跳
- [ ] 1.2 测试告警广播
  - [ ] 发送测试告警
  - [ ] 验证 WebSocket 推送
  - [ ] 验证多客户端接收
- [ ] 1.3 测试流服务集成
  - [ ] 启动流服务
  - [ ] 发送告警
  - [ ] 确认 WebSocket 广播
- [ ] 1.4 创建测试脚本

**预期成果**:

- ✅ 后端 WebSocket 功能验证通过
- ✅ 告警实时广播正常工作

---

### Day 2: 前端 WebSocket 客户端

**目标**: 实现前端 WebSocket 连接和消息接收

**任务**:

- [ ] 2.1 修复前端 WebSocket 配置
  - [ ] 修复环境变量配置
  - [ ] 修复 WebSocket URL
  - [ ] 添加 token 传递
- [ ] 2.2 集成到 Wazuh 页面
  - [ ] 导入 WazuhWebSocketClient
  - [ ] 初始化连接
  - [ ] 处理接收到的告警
- [ ] 2.3 实现消息处理
  - [ ] 接收 alert 消息
  - [ ] 更新告警列表
  - [ ] 更新统计数据
- [ ] 2.4 错误处理
  - [ ] 连接失败处理
  - [ ] 消息解析错误处理
  - [ ] 用户提示

**预期成果**:

- ✅ 前端可以连接 WebSocket
- ✅ 可以接收告警消息
- ✅ 告警自动显示在页面上

---

### Day 3: 实时更新和自动重连

**目标**: 实现完整的实时用户体验

**任务**:

- [ ] 3.1 实时统计更新
  - [ ] 统计数字自动更新
  - [ ] 颜色动态变化
  - [ ] 动画效果
- [ ] 3.2 告警列表实时追加
  - [ ] 新告警顶部显示
  - [ ] 平滑动画
  - [ ] 自动滚动
- [ ] 3.3 连接状态指示器
  - [ ] 绿色 = 已连接
  - [ ] 红色 = 断开
  - [ ] 黄色 = 连接中
- [ ] 3.4 自动重连机制
  - [ ] 断线自动重连
  - [ ] 指数退避
  - [ ] 最大重试次数
  - [ ] 手动重连按钮

**预期成果**:

- ✅ 完整的实时更新体验
- ✅ 稳定的连接管理
- ✅ 友好的用户提示

---

### Day 4: 测试和文档

**目标**: 完成测试验证和文档编写

**任务**:

- [ ] 4.1 功能测试
  - [ ] 单客户端测试
  - [ ] 多客户端测试
  - [ ] 压力测试
  - [ ] 长时间稳定性测试
- [ ] 4.2 性能测试
  - [ ] 连接数测试
  - [ ] 消息频率测试
  - [ ] 内存泄漏检查
- [ ] 4.3 文档编写
  - [ ] WebSocket 使用指南
  - [ ] API 文档更新
  - [ ] Week 2 完成报告
- [ ] 4.4 问题修复
  - [ ] 测试发现的问题
  - [ ] 边缘情况处理
  - [ ] 性能优化

**预期成果**:

- ✅ 所有测试通过
- ✅ 文档齐全
- ✅ Week 2 完成

---

## 📁 文件结构

### 新建文件

```
tests/
├── test_websocket_connection.py   # WebSocket 连接测试
├── test_websocket_broadcast.py    # 广播功能测试
└── test_websocket_stress.py       # 压力测试

docs/week2/
├── README_WEEK2.md                 # Week 2 说明
├── WEBSOCKET_IMPLEMENTATION.md     # 实施文档
├── WEBSOCKET_TEST_REPORT.md        # 测试报告
└── WEEK2_COMPLETION_REPORT.md      # 完成报告
```

### 修改文件

```
frontend/
├── lib/wazuhWebSocket.ts           # 修复配置
├── components/wazuh/WazuhAlertStream.tsx  # 集成 WebSocket
└── app/[locale]/wazuh/page.tsx      # 使用 WebSocket 版本

backend/
└── services/wazuh_stream_service.py # 已完善，无需修改
```

---

## 🧪 测试计划

### 单元测试

```python
# WebSocket 连接测试
def test_websocket_connection():
    # 1. 测试未认证连接被拒绝
    # 2. 测试有效 token 连接成功
    # 3. 测试 ping/pong 心跳
    # 4. 测试订阅 channels
    pass

# 广播功能测试
def test_broadcast_alert():
    # 1. 发送测试告警
    # 2. 验证所有客户端收到
    # 3. 验证消息格式正确
    pass
```

### 集成测试

```bash
# 1. 启动后端
cd backend && python main.py

# 2. 启动流服务
curl -X POST http://localhost:8000/api/v1/wazuh/stream/start \
  -H "Authorization: Bearer $TOKEN"

# 3. 测试 WebSocket
python tests/test_websocket_connection.py

# 4. 测试广播
python tests/test_websocket_broadcast.py
```

### 浏览器测试

```javascript
// 浏览器控制台
const ws = new WebSocket("ws://localhost:8000/ws/alerts?token=" + token);

ws.onmessage = event => {
  console.log("收到消息:", event.data);
};
```

---

## 🎯 验收标准

### 功能验收

- [ ] WebSocket 连接成功率 > 99%
- [ ] 告警实时推送延迟 < 1 秒
- [ ] 支持 10+ 并发连接
- [ ] 自动重连成功率 > 95%
- [ ] 统计数据实时更新

### 性能验收

- [ ] 内存使用稳定（无泄漏）
- [ ] CPU 使用率正常
- [ ] 长时间运行稳定（24 小时+）

### 用户体验验收

- [ ] 连接状态清晰可见
- [ ] 断线有友好提示
- [ ] 重连无需手动操作
- [ ] 告警显示流畅无卡顿

---

## 📊 Week 2 成功标准

### 核心目标

✅ **后端 WebSocket**: 已有完整实现，验证即可
✅ **前端 WebSocket 客户端**: 完整实现
✅ **实时推送功能**: 告警实时显示
✅ **自动重连**: 断线自动恢复

### 交付物

- [ ] 前端 WebSocket 集成完成
- [ ] 实时更新功能实现
- [ ] 测试脚本编写完成
- [ ] 文档编写完成
- [ ] 所有测试通过

---

## 🚀 下一步行动

1. **立即开始**: Day 1 - 后端测试验证
2. **创建测试脚本**: WebSocket 连接和广播测试
3. **验证现有功能**: 确保后端工作正常
4. **前端开发**: Day 2-3

---

**Week 2 状态**: 🚀 **准备开始！**

**预计完成日期**: 2026-03-01 (4 天后)

**责任人**: SOC Copilot Team

🎯 **目标**: 完整的 WebSocket 实时推送功能！\*\*
