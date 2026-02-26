#!/bin/bash
# Quick Wazuh Integration Setup (Non-Interactive)
# For testing and development

set -e

echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║          Wazuh Integration Quick Setup (Testing Mode)            ║"
echo "║                      SOC Copilot v1.0.0                           ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

# Check if .env exists
if [ ! -f .env ]; then
    print_warning ".env file not found, creating from example..."
    cp .env.example .env
fi

echo ""
echo "Configuration: Testing Mode (No Wazuh Connection Required)"
echo ""

# Add Wazuh configuration to .env
cat >> .env << 'EOF'

# Wazuh SIEM Integration - Testing Configuration
WAZUH_ENABLED=true
WAZUH_REQUIRED=false  # Don't fail if Wazuh is not available
WAZUH_API_URL=https://wazuh.example.com:55000
WAZUH_API_USERNAME=wazuh-wui
WAZUH_API_PASSWORD=testing-password-change-me
WAZUH_VERIFY_SSL=false  # For testing with self-signed certs
WAZUH_RECEIVER_ENABLED=true
WAZUH_RECEIVER_AUTO_START=false  # Don't auto-start (no real Wazuh)
WAZUH_POLL_INTERVAL=30
WAZUH_BATCH_SIZE=100
WAZUH_LOOKBACK_MINUTES=5
EOF

print_success ".env file configured for testing"

echo ""
echo "Installing Python dependencies..."
cd backend
pip install pyjwt==2.8.0 aiohttp==3.9.1 backoff==2.2.1 -q 2>/dev/null
cd ..
print_success "Dependencies installed"

echo ""
echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║                      Setup Complete!                            ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
echo ""

print_success "Wazuh integration configured!"
echo ""
echo "Next Steps:"
echo ""
echo "1. For Testing (No Wazuh Required):"
echo "   • Backend will start with Wazuh enabled but receiver stopped"
echo "   • You can create test alerts via API"
echo "   • Run: python test_wazuh_integration.py"
echo ""
echo "2. For Production (With Real Wazuh):"
echo "   • Edit .env and set your Wazuh credentials:"
echo "     - WAZUH_API_URL=your-wazuh-url"
echo "     - WAZUH_API_PASSWORD=your-password"
echo "   • Set WAZUH_RECEIVER_AUTO_START=true"
echo "   • Restart: docker-compose restart backend"
echo ""
echo "Test Commands:"
echo "  • Check status: curl http://localhost:8000/api/v1/wazuh/integration/status"
echo "  • Create test alert: curl -X POST http://localhost:8000/api/v1/wazuh/test-alert"
echo ""
echo "Documentation: docs/wazuh_integration.md"
echo ""
