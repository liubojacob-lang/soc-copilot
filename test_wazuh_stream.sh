#!/bin/bash
# Wazuh Stream Service 启动脚本

echo "启动 Wazuh 实时流服务..."

# 获取 JWT Token (请先登录获取)
#TOKEN="your_jwt_token_here"

# 启动流服务
echo "1. 启动 Wazuh 流服务..."
curl -X POST http://localhost:8000/api/v1/wazuh/stream/start \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "config": {
      "aggregation_window_seconds": 60,
      "max_buffer_size": 10000,
      "max_history_size": 1000
    }
  }'

echo ""
echo "2. 检查服务状态..."
curl -s http://localhost:8000/api/v1/wazuh/stream/status \
  -H "Authorization: Bearer $TOKEN" | jq '.'

echo ""
echo "3. 发送测试告警..."
curl -X POST http://localhost:8000/api/v1/wazuh/stream/test-alert \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "agent_id": "001",
    "severity": "high",
    "event_type": "ssh_bruteforce",
    "count": 3
  }'

echo ""
echo "完成！现在刷新浏览器，应该能看到测试告警了。"
