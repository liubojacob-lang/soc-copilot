#!/bin/bash
# Fix and Start Wazuh API

set -e

echo "═══════════════════════════════════════════════════════════════"
echo "  Wazuh API Fix Script"
echo "═══════════════════════════════════════════════════════════════"
echo ""

CONTAINER="soc-wazuh-manager"

echo "1. Checking container status..."
if ! docker ps | grep -q $CONTAINER; then
    echo "❌ Container $CONTAINER is not running"
    exit 1
fi
echo "✅ Container is running"
echo ""

echo "2. Backing up existing API configuration..."
docker exec $CONTAINER cp /var/ossec/api/configuration/api.yaml /var/ossec/api/configuration/api.yaml.bak
echo "✅ Backup created"
echo ""

echo "3. Enabling HTTP API (no SSL)..."
docker exec $CONTAINER bash -c 'cat > /var/ossec/api/configuration/api.yaml << EOF
host: ["0.0.0.0", "::"]
port: 55000

# Disable HTTPS for development
https:
  enabled: no

# Logging
logs:
  level: "info"
  format: "plain"

# CORS
cors:
  enabled: yes
  source_route: "*"
  expose_headers: "*"
  allow_headers: "*"
  allow_credentials: no

# Access
access:
  max_login_attempts: 50
  block_time: 300
  max_request_per_minute: 300

# Drop privileges
drop_privileges: yes

# Max upload size
max_upload_size: 10485760
EOF
'
echo "✅ API configuration updated"
echo ""

echo "4. Checking for API binary..."
if docker exec $CONTAINER test -f /usr/bin/wazuh-api; then
    echo "✅ Found wazuh-api at /usr/bin/wazuh-api"
    API_BIN="/usr/bin/wazuh-api"
elif docker exec $CONTAINER test -f /var/ossec/api/scripts/wazuh-api; then
    echo "✅ Found wazuh-api at /var/ossec/api/scripts/wazuh-api"
    API_BIN="/var/ossec/api/scripts/wazuh-api"
else
    echo "❌ wazuh-api binary not found"
    echo "   This Wazuh container may not include the API component"
    echo ""
    echo "   Alternative: Use official Wazuh API container"
    exit 1
fi
echo ""

echo "5. Starting Wazuh API..."
docker exec $CONTAINER bash -c "cd /var/ossec && $API_BIN --config /var/ossec/api/configuration/api.yaml > /tmp/wazuh-api.log 2>&1 &" &
sleep 3
echo "✅ API start command executed"
echo ""

echo "6. Checking if API is running..."
if docker exec $CONTAINER ps aux | grep -q "[w]azuh-api"; then
    echo "✅ Wazuh API process is running!"
else
    echo "⚠️  API process not found in process list"
    echo "   Checking logs..."
    docker exec $CONTAINER cat /tmp/wazuh-api.log 2>/dev/null | tail -20 || echo "   No log file found"
fi
echo ""

echo "7. Testing API connectivity..."
sleep 2
if curl -s http://localhost:55000/ > /dev/null 2>&1; then
    echo "✅ API is responding on http://localhost:55000"
else
    echo "⚠️  API not responding yet"
    echo "   This may take a few more seconds..."
    echo "   Check logs: docker logs $CONTAINER"
fi
echo ""

echo "═══════════════════════════════════════════════════════════════"
echo "  Summary"
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo "API Configuration:"
echo "  URL: http://localhost:55000"
echo "  Username: wazuh-wui"
echo "  Password: wazuh-ui-wazuh-wui"
echo ""
echo "Test Commands:"
echo "  curl http://localhost:55000/"
echo "  curl -u wazuh-wui:wazuh-ui-wazuh-wui http://localhost:55000/health"
echo ""
echo "Logs:"
echo "  docker logs $CONTAINER"
echo "  docker exec $CONTAINER cat /tmp/wazuh-api.log"
echo ""
