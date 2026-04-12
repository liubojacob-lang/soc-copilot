# Wazuh 实时流连接问题 - 诊断和解决

## 问题描述

访问 `http://localhost:3003/zh/wazuh` 页面显示"未连接到 Wazuh 实时流"。

## 根本原因

1. **Wazuh 集成默认禁用** (`wazuh_enabled = False`)
2. **Wazuh 流服务未启动** - 需要手动调用 API
3. **可能缺少 Wazuh 服务器** - 用于实际告警数据源

## 快速解决方案

### 方案 A: 启用并配置 Wazuh（如果有 Wazuh 服务器）

1. **配置环境变量**

编辑 `backend/.env`（或创建）：

```bash
# 启用 Wazuh
WAZUH_ENABLED=true
WAZUH_REQUIRED=false

# Wazuh API 连接配置
WAZUH_API_URL=https://your-wazuh-server:55000
WAZUH_API_USERNAME=wazuh-wui
WAZUH_API_PASSWORD=your_password
WAZUH_VERIFY_SSL=false

# 启用日志接收器
WAZUH_RECEIVER_ENABLED=true
WAZUH_RECEIVER_AUTO_START=true
```

2. **重启后端**

```bash
cd backend
python main.py
```

3. **启动流服务**

```bash
# 登录前端获取 JWT Token
TOKEN="your_jwt_token"

# 启动服务
curl -X POST http://localhost:8000/api/v1/wazuh/stream/start \
  -H "Authorization: Bearer $TOKEN"
```

4. **验证状态**

```bash
curl http://localhost:8000/api/v1/wazuh/stream/status \
  -H "Authorization: Bearer $TOKEN"
```

### 方案 B: 测试模式（无需 Wazuh 服务器）

如果暂时没有 Wazuh 服务器，可以用测试模式：

1. **确保后端运行**

```bash
cd backend
python main.py
```

2. **启动流服务**

```bash
TOKEN="your_jwt_token"

curl -X POST http://localhost:8000/api/v1/wazuh/stream/start \
  -H "Authorization: Bearer $TOKEN"
```

3. **发送测试告警**

```bash
curl -X POST http://localhost:8000/api/v1/wazuh/stream/test-alert \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "agent_id": "001",
    "severity": "high",
    "event_type": "ssh_login",
    "count": 5
  }'
```

4. **刷新浏览器** - 前端应该会显示连接成功并接收测试告警

## 故障排除

### 检查后端日志

```bash
cd backend
tail -f server.err
```

查找 Wazuh 相关日志：

```
- "Wazuh client initialized"
- "Wazuh alert stream service initialized"
- "Wazuh log receiver started"
```

### 检查服务状态

```bash
# 流服务状态
curl http://localhost:8000/api/v1/wazuh/stream/status

# 订阅统计
curl http://localhost:8000/api/v1/wazuh/stream/subscriptions
```

### 前端调试

打开浏览器开发者工具（F12）：

1. **Console 标签** - 查看 WebSocket 连接错误
2. **Network 标签** - 筛选 "WS" 查看 WebSocket 连接
3. **查看请求 URL** - 应该类似：
   ```
   ws://localhost:8000/api/v1/ws/alerts?token=xxx&channels=wazuh
   ```

### 常见错误和解决

#### 错误 1: 404 Not Found

**原因**: WebSocket 端点不存在
**解决**: 确保后端正在运行，检查端口 8000

#### 错误 2: 401 Unauthorized

**原因**: Token 无效或过期
**解决**: 重新登录获取新 Token

#### 错误 3: "Disconnected" 持续显示

**原因**:

- 流服务未启动
- Wazuh 集成未启用
- 无告警数据推送

**解决**:

1. 确认 `WAZUH_ENABLED=true`
2. 调用 `/api/v1/wazuh/stream/start` 启动服务
3. 发送测试告警验证

#### 错误 4: 连接成功但无告警

**原因**: 无实际的 Wazuh 告警数据源
**解决**:

- 配置真实的 Wazuh API 连接
- 或使用测试告警 API 验证功能

## 自动化启动脚本

您可以使用提供的脚本一键启动：

```bash
chmod +x test_wazuh_stream.sh
./test_wazuh_stream.sh
```

## 相关文档

- Wazuh 集成: `docs/WAZUH_QUICKREF.md`
- 部署指南: `docs/WAZUH_DEPLOYMENT.md`
- API 文档: `docs/02-api-overview.md`

---

**需要帮助？**

1. 检查后端日志: `tail -f backend/server.err`
2. 检查服务状态: `curl http://localhost:8000/api/health`
3. 查看浏览器控制台错误
