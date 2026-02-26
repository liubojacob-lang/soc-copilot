#!/bin/bash
# 发送多条不同类型的测试告警到 Loki

echo "=== 发送测试告警到 Loki ==="
echo ""

# 当前时间戳（纳秒）
TIMESTAMP=$(date +%s)000000000

echo "1️⃣ 发送高危告警..."
curl -X POST http://localhost:3100/loki/api/v1/push \
  -H 'Content-Type: application/json' \
  -d "{
    \"streams\": [
      {
        \"stream\": {
          \"job\": \"soc-copilot\",
          \"level\": \"critical\",
          \"event_type\": \"malware_detected\",
          \"agent_id\": \"agent-001\",
          \"source_ip\": \"192.168.1.100\"
        },
        \"values\": [
          [\"$TIMESTAMP\", \"{\\\"message\\\": \\\"Malware detected on host\\\", \\\"file\\\": \\\"trojan.exe\\\", \\\"action\\\": \\\"quarantined\\\"}\"]
        ]
      }
    ]
  }" 2>&1 | grep -v "Total\|Dload" || echo "✅ 发送完成"

echo ""
echo "2️⃣ 发送 SSH 暴力破解告警..."
TIMESTAMP2=$(date +%s)000000000
curl -X POST http://localhost:3100/loki/api/v1/push \
  -H 'Content-Type: application/json' \
  -d "{
    \"streams\": [
      {
        \"stream\": {
          \"job\": \"soc-copilot\",
          \"level\": \"high\",
          \"event_type\": \"ssh_bruteforce\",
          \"agent_id\": \"agent-002\",
          \"source_ip\": \"10.0.0.5\"
        },
        \"values\": [
          [\"$TIMESTAMP2\", \"{\\\"message\\\": \\\"SSH brute force attack detected\\\", \\\"attempts\\\": 100, \\\"username\\\": \\\"root\\\"}\"]
        ]
      }
    ]
  }" 2>&1 | grep -v "Total\|Dload" || echo "✅ 发送完成"

echo ""
echo "3️⃣ 发送端口扫描告警..."
TIMESTAMP3=$(date +%s)000000000
curl -X POST http://localhost:3100/loki/api/v1/push \
  -H 'Content-Type: application/json' \
  -d "{
    \"streams\": [
      {
        \"stream\": {
          \"job\": \"soc-copilot\",
          \"level\": \"medium\",
          \"event_type\": \"port_scan\",
          \"agent_id\": \"agent-003\",
          \"source_ip\": \"172.16.0.50\"
        },
        \"values\": [
          [\"$TIMESTAMP3\", \"{\\\"message\\\": \\\"Port scan detected\\\", \\\"scanned_ports\\\": [22, 80, 443, 3306], \\\"duration\\\": \\\"5s\\\"}\"]
        ]
      }
    ]
  }" 2>&1 | grep -v "Total\|Dload" || echo "✅ 发送完成"

echo ""
echo "4️⃣ 发送信息日志..."
TIMESTAMP4=$(date +%s)000000000
curl -X POST http://localhost:3100/loki/api/v1/push \
  -H 'Content-Type: application/json' \
  -d "{
    \"streams\": [
      {
        \"stream\": {
          \"job\": \"soc-copilot\",
          \"level\": \"info\",
          \"event_type\": \"system_info\",
          \"agent_id\": \"system\",
          \"source_ip\": \"127.0.0.1\"
        },
        \"values\": [
          [\"$TIMESTAMP4\", \"{\\\"message\\\": \\\"System health check completed\\\", \\\"status\\\": \\\"healthy\\\", \\\"uptime\\\": 3600}\"]
        ]
      }
    ]
  }" 2>&1 | grep -v "Total\|Dload" || echo "✅ 发送完成"

echo ""
echo "✅ 所有测试告警已发送！"
echo ""
echo "现在在 Grafana 中查看："
echo "  1. Explore → Loki 数据源"
echo "  2. 查询: {job=\"soc-copilot\"}"
echo "  3. 时间范围: Last 5 minutes"
echo "  4. Run query"
