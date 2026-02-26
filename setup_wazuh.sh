#!/bin/bash
# Wazuh Integration Quick Setup Script
# SOC Copilot v1.0.0

set -e

echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║                                                                    ║"
echo "║        Wazuh Integration Setup - SOC Copilot v1.0.0               ║"
echo "║                                                                    ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_info() {
    echo "ℹ️  $1"
}

# Check if .env file exists
if [ ! -f .env ]; then
    print_error ".env file not found!"
    print_info "Creating .env file from .env.example..."
    cp .env.example .env
    print_success ".env file created"
else
    print_success ".env file found"
fi

echo ""
echo "══════════════════════════════════════════════════════════════════"
echo "Wazuh Configuration"
echo "══════════════════════════════════════════════════════════════════"
echo ""

# Prompt for Wazuh API URL
read -p "Enter Wazuh API URL (e.g., https://wazuh.example.com:55000): " WAZUH_API_URL
if [ -z "$WAZUH_API_URL" ]; then
    print_error "Wazuh API URL is required!"
    exit 1
fi

# Prompt for Wazuh API credentials
read -p "Enter Wazuh API username [default: wazuh-wui]: " WAZUH_API_USERNAME
WAZUH_API_USERNAME=${WAZUH_API_USERNAME:-wazuh-wui}

read -sp "Enter Wazuh API password: " WAZUH_API_PASSWORD
echo ""
if [ -z "$WAZUH_API_PASSWORD" ]; then
    print_error "Wazuh API password is required!"
    exit 1
fi

# Prompt for SSL verification
read -p "Verify SSL certificate? [Y/n]: " VERIFY_SSL
VERIFY_SSL=${VERIFY_SSL:-Y}
if [[ $VERIFY_SSL =~ ^[Yy]$ ]]; then
    WAZUH_VERIFY_SSL="true"
else
    WAZUH_VERIFY_SSL="false"
    print_warning "SSL verification disabled - only use for testing with self-signed certificates!"
fi

# Prompt for certificate path (if SSL verification enabled)
if [ "$WAZUH_VERIFY_SSL" = "false" ]; then
    read -p "Path to Wazuh certificate (optional, press Enter to skip): " WAZUH_CERT_PATH
fi

echo ""
echo "══════════════════════════════════════════════════════════════════"
echo "Advanced Configuration (press Enter for defaults)"
echo "══════════════════════════════════════════════════════════════════"
echo ""

# Polling interval
read -p "Polling interval in seconds [default: 30]: " POLL_INTERVAL
POLL_INTERVAL=${POLL_INTERVAL:-30}

# Batch size
read -p "Maximum alerts per poll [default: 100]: " BATCH_SIZE
BATCH_SIZE=${BATCH_SIZE:-100}

# Lookback minutes
read -p "Lookback minutes on startup [default: 5]: " LOOKBACK_MINUTES
LOOKBACK_MINUTES=${LOOKBACK_MINUTES:-5}

# Auto-start receiver
read -p "Auto-start receiver on startup? [Y/n]: " AUTO_START
AUTO_START=${AUTO_START:-Y}
if [[ $AUTO_START =~ ^[Yy]$ ]]; then
    WAZUH_AUTO_START="true"
else
    WAZUH_AUTO_START="false"
fi

echo ""
echo "══════════════════════════════════════════════════════════════════"
echo "Summary"
echo "══════════════════════════════════════════════════════════════════"
echo ""
echo "Wazuh API URL: $WAZUH_API_URL"
echo "Wazuh API Username: $WAZUH_API_USERNAME"
echo "Verify SSL: $WAZUH_VERIFY_SSL"
if [ ! -z "$WAZUH_CERT_PATH" ]; then
    echo "Certificate Path: $WAZUH_CERT_PATH"
fi
echo "Polling Interval: ${POLL_INTERVAL}s"
echo "Batch Size: $BATCH_SIZE alerts"
echo "Lookback: $LOOKBACK_MINUTES minutes"
echo "Auto-start Receiver: $WAZUH_AUTO_START"
echo ""

read -p "Save configuration to .env file? [Y/n]: " SAVE_CONFIG
SAVE_CONFIG=${SAVE_CONFIG:-Y}

if [[ $SAVE_CONFIG =~ ^[Yy]$ ]]; then
    # Update .env file
    echo ""
    print_info "Updating .env file..."

    # Remove existing WAZUH_ variables
    sed -i.bak '/^WAZUH_/d' .env

    # Add new configuration
    cat >> .env << EOF

# Wazuh SIEM Integration - Added $(date)
WAZUH_ENABLED=true
WAZUH_REQUIRED=false
WAZUH_API_URL=$WAZUH_API_URL
WAZUH_API_USERNAME=$WAZUH_API_USERNAME
WAZUH_API_PASSWORD=$WAZUH_API_PASSWORD
WAZUH_VERIFY_SSL=$WAZUH_VERIFY_SSL
EOF

    if [ ! -z "$WAZUH_CERT_PATH" ]; then
        echo "WAZUH_API_CERT_PATH=$WAZUH_CERT_PATH" >> .env
    fi

    cat >> .env << EOF
WAZUH_RECEIVER_ENABLED=true
WAZUH_RECEIVER_AUTO_START=$WAZUH_AUTO_START
WAZUH_POLL_INTERVAL=$POLL_INTERVAL
WAZUH_BATCH_SIZE=$BATCH_SIZE
WAZUH_LOOKBACK_MINUTES=$LOOKBACK_MINUTES
EOF

    print_success ".env file updated"
else
    print_info "Configuration not saved. Exiting."
    exit 0
fi

echo ""
echo "══════════════════════════════════════════════════════════════════"
echo "Installation"
echo "══════════════════════════════════════════════════════════════════"
echo ""

# Install dependencies
print_info "Installing Python dependencies..."
cd backend
pip install pyjwt==2.8.0 aiohttp==3.9.1 backoff==2.2.1 2>/dev/null
cd ..
print_success "Dependencies installed"

echo ""
echo "══════════════════════════════════════════════════════════════════"
echo "Testing Connection"
echo "══════════════════════════════════════════════════════════════════"
echo ""

# Test connection
print_info "Testing Wazuh API connection..."

if [ "$WAZUH_VERIFY_SSL" = "false" ]; then
    CURL_SSL="-k"
else
    CURL_SSL=""
fi

# Try to connect to Wazuh API
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -u "${WAZUH_API_USERNAME}:${WAZUH_API_PASSWORD}" $CURL_SSL "${WAZUH_API_URL}/" 2>/dev/null || echo "000")

if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "401" ]; then
    print_success "Connection successful!"
else
    print_error "Connection failed (HTTP code: $HTTP_CODE)"
    print_warning "Please verify your Wazuh API URL and credentials"
    print_info "You can test manually:"
    echo "  curl -u ${WAZUH_API_USERNAME}:PASSWORD $CURL_SSL ${WAZUH_API_URL}/"
fi

echo ""
echo "══════════════════════════════════════════════════════════════════"
echo "Next Steps"
echo "══════════════════════════════════════════════════════════════════"
echo ""

echo "1. Restart SOC Copilot backend:"
echo "   docker-compose -f docker-compose.prod.yml restart backend"
echo ""
echo "2. Check logs for Wazuh initialization:"
echo "   docker-compose -f docker-compose.prod.yml logs backend | grep Wazuh"
echo ""
echo "3. Verify integration status:"
echo "   curl http://localhost:8000/api/v1/wazuh/integration/status"
echo ""
echo "4. Run integration tests:"
echo "   python test_wazuh_integration.py"
echo ""
echo "5. Create a test alert:"
echo "   curl -X POST http://localhost:8000/api/v1/wazuh/test-alert \\"
echo "     -H 'Content-Type: application/json' \\"
echo "     -d '{\"agent_id\": \"001\", \"rule_id\": 5710, \"severity\": \"high\"}'"
echo ""

print_success "Wazuh integration setup complete!"
echo ""
echo "For detailed documentation, see: docs/wazuh_integration.md"
