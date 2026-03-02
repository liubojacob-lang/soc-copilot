# Wazuh 测试模式使用指南

由于 ARM64 架构限制，我们使用测试模式来验证 Wazuh 集成。

## 快速开始

### 1. 启动 Wazuh 流服务（测试模式）

后端已经配置好，只需要启动流服务：

```bash
# 登录前端获取 JWT Token
# 浏览器访问: http://localhost:3003/zh/login

# 打开浏览器开发者工具 (F12)，在 Console 中运行：
const token = localStorage.getItem('access_token');
console.log('Token:', token);

# 复制 token 后，在终端运行：
TOKEN="your_token_here"
curl -X POST http://localhost:8000/api/v1/wazuh/stream/start \
  -H "Authorization: Bearer $TOKEN"
```

### 2. 发送测试告警

```bash
curl -X POST http://localhost:8000/api/v1/wazuh/stream/test-alert \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "agent_id": "001",
    "severity": "high",
    "event_type": "ssh_bruteforce",
    "count": 3
  }'
```

### 3. 查看前端

访问: `http://localhost:3003/zh/wazuh`

应该能看到：
- ✅ 已连接到 Wazuh 实时流
- 实时接收的测试告警

## 工作原理

测试模式不需要真实的 Wazuh 服务器：
- Backend 模拟生成 Wazuh 告警
- 通过 WebSocket 推送到前端
- 验证整个数据流

## 后续：使用真实 Wazuh

如果需要真实的 Wazuh 服务：

### 选项 A: 使用云服务
- Wazuh Cloud: https://wazuh.com/cloud
- AWS/Azure/GCP 上的 Wazuh

### 选项 B: x86_64 虚拟机
在 VM 中运行 Wazuh（需要 Intel/AMD 架构）

### 选项 C: 修复现有 Wazuh
手动修改配置文件：
```bash
# 需要管理员权限
sudo nano /Users/levent/Desktop/sec/config/wazuh/ossec.conf
```

找到并注释掉 `host-deny` 部分：
```xml
<!--
<active-response>
  <disabled>no</disabled>
  <command>host-deny</command>  <-- 注释掉这个
  ...
</active-response>
-->
```

然后重启：
```bash
docker restart soc-wazuh-manager
```

## 故障排除

### 前端显示"未连接"
1. 检查 backend 是否运行
2. 启动流服务（见步骤1）
3. 检查浏览器控制台错误

### 发送测试告警无响应
1. 确认流服务已启动
2. 检查 JWT Token 是否有效
3. 查看 backend 日志: `tail -f backend/server.err`

## 相关文件

- `test_wazuh_stream.sh` - 测试脚本
- `WAZUH_STREAM_TROUBLESHOOT.md` - 故障排除
- `docs/WAZUH_INSTALLATION.md` - 完整安装指南
