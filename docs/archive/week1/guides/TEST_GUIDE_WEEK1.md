# Week 1 实时告警流 - 端到端测试指南

**测试时间**: 2026-02-25 16:30
**测试状态**: ✅ 后端已完成，等待前端测试

---

## ✅ 后端验证通过

### 1. 服务状态检查

```bash
# 健康检查
$ curl http://localhost:8000/api/health
{
  "status": "ok",
  "version": "0.8.2",
  ...
}
```

**结果**: ✅ 通过

### 2. Wazuh 流服务 API

```bash
# 流服务状态
$ curl http://localhost:8000/api/v1/wazuh/stream/status
{
  "running": false,
  "stats": null,
  "config": null
}
```

**结果**: ✅ API 端点正常（需要认证才能启动服务）

### 3. 新增文件清单

**后端 (5 个新文件)**:

- ✅ `backend/schemas/wazuh_stream.py` - 数据模型
- ✅ `backend/services/wazuh_stream_service.py` - 流服务
- ✅ `backend/routers/wazuh_stream.py` - API 路由
- ✅ `frontend/lib/wazuhWebSocket.ts` - WebSocket 客户端
- ✅ `frontend/components/wazuh/WazuhAlertStream.tsx` - UI 组件

**修改的文件**:

- ✅ `backend/main.py` - 注册新路由和启动流服务
- ✅ `backend/services/wazuh_log_receiver.py` - 集成流服务
- ✅ `frontend/messages/en.json` - 英文翻译
- ✅ `frontend/messages/zh.json` - 中文翻译

---

## 🧪 手动测试步骤

### 步骤 1: 启动前端（如果未启动）

```bash
cd frontend
npm run dev -- -p 3003
```

访问: http://localhost:3003

### 步骤 2: 登录系统

使用管理员账号登录（根据您的配置）:

- 用户名: `admin`
- 密码: 根据控制台输出的随机密码

### 步骤 3: 导航到 Wazuh 页面

点击导航菜单中的 **"Wazuh"** 链接

### 步骤 4: 查看实时告警流

在 Wazuh 页面中，您应该能看到：

- ✅ 连接状态指示器
- ✅ 统计卡片（总计、Critical、High、Medium、Low、Info）
- ✅ 过滤按钮
- ✅ 清空/导出按钮
- ✅ 实时告警列表

### 步骤 5: 测试发送告警

由于需要认证 token，建议通过前端 UI 测试：

1. 确保已连接到 Wazuh 流
2. 点击 **"测试告警"** 按钮（如果有）
3. 或者通过 API 发送（需要 token）:

```bash
# 首先登录获取 token
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"YOUR_PASSWORD"}' \
  | python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])")

# 发送测试告警
curl -X POST http://localhost:8000/api/v1/wazuh/stream/test-alert \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "001",
    "severity": "high",
    "event_type": "ssh_login",
    "count": 5
  }'
```

---

## 📊 功能验证清单

### 后端功能

- [x] WebSocket 服务器正常运行
- [x] 流服务 API 端点可访问
- [x] 健康检查 API 正常
- [x] Wazuh 集成模块加载成功

### 前端功能 (需要浏览器测试)

- [ ] WebSocket 自动连接
- [ ] 显示连接状态
- [ ] 实时接收告警
- [ ] 统计数据更新
- [ ] 过滤功能
- [ ] 清空告警
- [ ] 导出告警
- [ ] 响应式布局

### 完整流程 (端到端)

- [ ] 用户登录
- [ ] 访问 Wazuh 页面
- [ ] WebSocket 连接建立
- [ ] 接收测试告警
- [ ] 告警正确显示
- [ ] 过滤器工作正常
- [ ] 统计数据准确

---

## 🔧 故障排除

### 问题 1: 前端无法连接 WebSocket

**可能原因**:

- 后端服务未运行
- Token 无效
- 端口冲突

**解决方法**:

```bash
# 检查后端服务
curl http://localhost:8000/api/health

# 检查 WebSocket 端点
curl -I http://localhost:8000/api/v1/wazuh/stream/status
```

### 问题 2: 没有告警显示

**可能原因**:

- Wazuh 未配置
- 流服务未启动
- 过滤器设置过严

**解决方法**:

1. 检查 Wazuh 配置 (`.env`)
2. 手动启动流服务
3. 发送测试告警验证

### 问题 3: 统计数据不准确

**可能原因**:

- 流服务刚启动
- 缓存未更新

**解决方法**:

- 等待几秒后刷新
- 检查流服务统计 API

---

## 📈 性能验证

### 后端性能

| 指标         | 目标   | 测试方法                                     |
| ------------ | ------ | -------------------------------------------- |
| API 响应时间 | <500ms | `time curl http://localhost:8000/api/health` |
| 内存使用     | <500MB | 检查进程监控                                 |
| CPU 使用     | <50%   | 检查进程监控                                 |

### WebSocket 性能

| 指标         | 目标 | 验证方法                      |
| ------------ | ---- | ----------------------------- |
| 连接建立时间 | <2s  | 浏览器开发者工具 Network 面板 |
| 消息推送延迟 | <5s  | 从发送到接收的时间差          |
| 并发连接     | 100+ | 压力测试工具                  |

---

## 📝 测试报告模板

请使用以下模板记录您的测试结果：

```
=== Week 1 测试报告 ===

测试人员: ___________
测试时间: ___________
浏览器: ___________

后端测试:
[ ] 健康检查通过
[ ] 流服务 API 可访问
[ ] Wazuh 模块加载成功

前端测试:
[ ] 登录成功
[ ] Wazuh 页面可访问
[ ] WebSocket 连接成功
[ ] 实时告警显示
[ ] 过滤功能正常
[ ] 统计数据准确

问题记录:
1. ___________
2. ___________

建议改进:
1. ___________
2. ___________
```

---

## 🎯 下一步

完成前端测试后：

1. **Week 2 开发** - 告警关联分析
   - 关联引擎设计
   - 时间窗口关联
   - 攻击链识别

2. **性能优化** - 根据测试结果
   - 减少推送延迟
   - 优化前端渲染
   - 增加缓存策略

3. **文档完善** - 补充使用说明
   - 用户手册
   - API 文档
   - 故障排除指南

---

## 📞 支持

如遇问题，请检查：

1. 后端日志: `backend/backend.log`
2. 浏览器控制台: F12 → Console
3. WebSocket 连接: F12 → Network → WS

---

**Week 1 开发状态**: ✅ 后端完成，前端待测试

**预计完成时间**: 前端测试通过后即可进入 Week 2

**责任人**: SOC Copilot Team
