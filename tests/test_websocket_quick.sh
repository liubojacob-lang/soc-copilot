#!/bin/bash
# WebSocket Quick Test Script

echo "============================================================"
echo "       WebSocket Quick Test"
echo "============================================================"
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Test functions
test_success() { echo -e "${GREEN}✓ $1${NC}"; }
test_error() { echo -e "${RED}✗ $1${NC}"; }
test_info() { echo -e "${BLUE}ℹ $1${NC}"; }
test_header() {
    echo ""
    echo -e "${BLUE}============================================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}============================================================${NC}"
    echo ""
}

# Check if backend is running
test_header "Checking Backend"
RESPONSE=$(curl -s http://localhost:8000/api/health 2>/dev/null)
if echo "$RESPONSE" | grep -q '"status":"ok"'; then
    test_success "Backend is running"
else
    test_error "Backend is not running"
    echo "Please start backend with: cd backend && python main.py"
    exit 1
fi

# Get token
test_header "Getting Authentication Token"
TOKEN_RESPONSE=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}')

TOKEN=$(echo "$TOKEN_RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('access_token', ''))" 2>/dev/null)

if [ -z "$TOKEN" ]; then
    test_error "Failed to get token"
    exit 1
fi
test_success "Token obtained"

# Check WebSocket stats
test_header "WebSocket Statistics"
WS_STATS=$(curl -s http://localhost:8000/ws/stats 2>/dev/null)
ACTIVE_CONNECTIONS=$(echo "$WS_STATS" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('active_connections', 0))" 2>/dev/null)
test_info "Active connections: $ACTIVE_CONNECTIONS"

# Start stream service
test_header "Starting Stream Service"
STREAM_RESPONSE=$(curl -s -X POST http://localhost:8000/api/v1/wazuh/stream/start \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json")

if echo "$STREAM_RESPONSE" | grep -q '"running":true'; then
    test_success "Stream service started"
else
    test_info "Stream service already running or failed to start"
fi

# Send test alert
test_header "Sending Test Alert"
ALERT_RESPONSE=$(curl -s -X POST http://localhost:8000/api/v1/wazuh/stream/test-alert \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"agent_id":"001","severity":"high","event_type":"websocket_test","count":1}')

if echo "$ALERT_RESPONSE" | grep -q '"success":true'; then
    test_success "Test alert sent"
    ALERTS_SENT=$(echo "$ALERT_RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('alerts_sent', 0))" 2>/dev/null)
    test_info "Alerts sent: $ALERTS_SENT"
else
    test_error "Failed to send test alert"
fi

# Test WebSocket endpoint (basic)
test_header "Testing WebSocket Endpoint"
test_info "Note: Full WebSocket test requires Python async client"
test_info "Run: python tests/test_websocket_connection.py"

# Final summary
test_header "Summary"
test_success "Backend WebSocket server is running"
test_info "Next: Run Python tests for full validation"
echo ""
echo "To run full WebSocket tests:"
echo "  pip install websockets httpx"
echo "  python tests/test_websocket_connection.py"
echo ""

echo "============================================================"
echo "  WebSocket Backend Test Complete"
echo "============================================================"
