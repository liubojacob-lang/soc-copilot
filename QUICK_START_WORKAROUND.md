# 临时解决方案 - 快速测试指南

## 问题说明

当前 Zhipu AI API 响应时间约为 30 秒，超过了浏览器的默认超时限制。

## 解决方案

### 方案 1: 使用 curl 直接测试 API（推荐）

```bash
curl -X POST "http://localhost:8000/api/analyze-alert" \
  -H "Content-Type: application/json" \
  -d '{"raw_log": "FAILED_LOGIN - User admin from IP 192.168.1.100"}'
```

### 方案 2: 增加 AI 响应速度

编辑 `backend/services/ai_service.py`，将 `max_tokens` 从 4096 减少到 2048：

```python
# 原来：
max_tokens=4096

# 改为：
max_tokens=2048
```

### 方案 3: 切换到更快的模型

如果 Zhipu 有更快的模型，可以切换：

```python
self.model = "glm-4-flash"  # 当前
# self.model = "glm-4-turbo"  # 更快的选项（如果可用）
```

### 方案 4: 禁用外部 TI 加速

确认 `backend/.env` 中设置了：
```ini
ALLOW_EXTERNAL_TI=false
```

### 方案 5: 使用较短的输入日志

将输入日志限制在 100 字符以内，可以显著加快响应时间。

## 长期解决方案

需要实现以下功能之一：
1. 后台任务系统 + 轮询
2. WebSocket 实时通信
3. Server-Sent Events (SSE)
4. 流式响应
