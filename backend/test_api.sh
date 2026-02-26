#!/bin/bash
# SOC Copilot API 测试脚本

echo "🧪 SOC Copilot API - 测试套件"
echo "================================"
echo ""

# 检查后端是否运行
echo -n "检查后端服务... "
if curl -s http://localhost:8000/ > /dev/null; then
    echo -e "\033[0;32m✅ 运行中\033[0m"
else
    echo -e "\033[0;31m❌ 未运行\033[0m"
    echo ""
    echo "请先启动后端服务："
    echo "  cd /Users/levent/Desktop/sec/backend"
    echo "  uvicorn main:app --reload"
    exit 1
fi

echo ""
echo "================================"
echo "测试 1: 发送告警"
echo "================================"

RESPONSE=$(curl -s -X POST http://localhost:8000/api/v1/security-alerts/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "source": "test",
    "event_id": "api-test-001",
    "timestamp": "2026-02-24T10:00:00Z",
    "event_type": "api_test",
    "severity": "info",
    "title": "API Test Alert",
    "description": "Testing alert ingestion via API",
    "source_ip": "192.168.1.100",
    "rule_id": "1001",
    "rule_level": 5
  }')

echo "响应: $RESPONSE" | python3 -m json.tool 2>/dev/null || echo "响应: $RESPONSE"

echo ""
echo "================================"
echo "测试 2: 查询告警列表"
echo "================================"

curl -s http://localhost:8000/api/v1/security-alerts/ | python3 -m json.tool 2>/dev/null || echo "无法查询告警列表"

echo ""
echo "================================"
echo "测试 3: 获取告警统计"
echo "================================"

curl -s http://localhost:8000/api/v1/security-alerts/stats/summary | python3 -m json.tool 2>/dev/null || echo "无法获取统计"

echo ""
echo "================================"
echo "测试 4: 威胁情报丰富化"
echo "================================"

ENRICH_RESPONSE=$(curl -s -X POST http://localhost:8000/api/v1/alert-enrichment/process/1)
echo "响应: $ENRICH_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "响应: $ENRICH_RESPONSE"

echo ""
echo "================================"
echo "测试 5: 丰富化统计"
echo "================================"

curl -s http://localhost:8000/api/v1/alert-enrichment/stats | python3 -m json.tool 2>/dev/null || echo "无法获取丰富化统计"

echo ""
echo "================================"
echo "✅ 测试完成！"
echo ""
echo "💡 提示："
echo "  - 查看完整 API 文档: http://localhost:8000/docs"
echo "  - 查看数据库测试: python test_security_alerts.py"
echo "  - 查看丰富化测试: python test_enrichment.py"
echo ""
