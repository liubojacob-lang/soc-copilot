#!/bin/bash
# Wazuh Integration Script for SOC Copilot
# This script configures SOC Copilot to connect to Wazuh

set -e

echo "================================"
echo "Wazuh Integration for SOC Copilot"
echo "================================"
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Check if Wazuh is running
echo -e "${YELLOW}Checking Wazuh services...${NC}"
if ! curl -k https://localhost:55000/healthcheck &> /dev/null; then
    echo -e "${RED}Error: Wazuh is not running${NC}"
    echo "Please start Wazuh first: ./setup_wazuh.sh"
    exit 1
fi
echo -e "${GREEN}✓ Wazuh is running${NC}"
echo ""

# Source environment variables
if [ -f .env.wazuh ]; then
    echo -e "${YELLOW}Loading Wazuh environment variables...${NC}"
    export $(cat .env.wazuh | grep -v '^#' | xargs)
    echo -e "${GREEN}✓ Environment variables loaded${NC}"
else
    echo -e "${YELLOW}No .env.wazuh found, using default values${NC}"
fi
echo ""

# Update backend .env
echo -e "${YELLOW}Configuring backend .env...${NC}"
if [ -f backend/.env ]; then
    # Update or add Wazuh configuration
    if grep -q "^WAZUH_ENABLED=" backend/.env; then
        sed -i '' 's/^WAZUH_ENABLED=.*/WAZUH_ENABLED=true/' backend/.env
    else
        echo "WAZUH_ENABLED=true" >> backend/.env
    fi

    if grep -q "^WAZUH_API_URL=" backend/.env; then
        sed -i '' 's|^WAZUH_API_URL=.*|WAZUH_API_URL=https://localhost:55000|' backend/.env
    else
        echo "WAZUH_API_URL=https://localhost:55000" >> backend/.env
    fi

    if grep -q "^WAZUH_API_USERNAME=" backend/.env; then
        sed -i '' 's/^WAZUH_API_USERNAME=.*/WAZUH_API_USERNAME=wazuh-wui/' backend/.env
    else
        echo "WAZUH_API_USERNAME=wazuh-wui" >> backend/.env
    fi

    if grep -q "^WAZUH_API_PASSWORD=" backend/.env; then
        sed -i '' 's/^WAZUH_API_PASSWORD=.*/WAZUH_API_PASSWORD=wazuh-wui-password/' backend/.env
    else
        echo "WAZUH_API_PASSWORD=wazuh-wui-password" >> backend/.env
    fi

    if grep -q "^WAZUH_VERIFY_SSL=" backend/.env; then
        sed -i '' 's/^WAZUH_VERIFY_SSL=.*/WAZUH_VERIFY_SSL=false/' backend/.env
    else
        echo "WAZUH_VERIFY_SSL=false" >> backend/.env
    fi

    if grep -q "^WAZUH_RECEIVER_ENABLED=" backend/.env; then
        sed -i '' 's/^WAZUH_RECEIVER_ENABLED=.*/WAZUH_RECEIVER_ENABLED=true/' backend/.env
    else
        echo "WAZUH_RECEIVER_ENABLED=true" >> backend/.env
    fi

    if grep -q "^WAZUH_RECEIVER_AUTO_START=" backend/.env; then
        sed -i '' 's/^WAZUH_RECEIVER_AUTO_START=.*/WAZUH_RECEIVER_AUTO_START=true/' backend/.env
    else
        echo "WAZUH_RECEIVER_AUTO_START=true" >> backend/.env
    fi

    echo -e "${GREEN}✓ Backend .env configured${NC}"
else
    echo -e "${RED}Error: backend/.env not found${NC}"
    echo "Please create backend/.env from backend/.env.example"
    exit 1
fi
echo ""

# Test Wazuh API connection
echo -e "${YELLOW}Testing Wazuh API connection...${NC}"
WAZUH_API_URL=${WAZUH_API_URL:-https://localhost:55000}
WAZUH_API_USERNAME=${WAZUH_API_USERNAME:-wazuh-wui}
WAZUH_API_PASSWORD=${WAZUH_API_PASSWORD:-wazuh-wui-password}

if curl -k -u ${WAZUH_API_USERNAME}:${WAZUH_API_PASSWORD} ${WAZUH_API_URL}/?pretty=true &> /dev/null; then
    echo -e "${GREEN}✓ Wazuh API connection successful${NC}"
else
    echo -e "${RED}Error: Cannot connect to Wazuh API${NC}"
    echo "Please check your credentials and URL"
    exit 1
fi
echo ""

# Restart backend
echo -e "${YELLOW}Do you want to restart the backend now? (y/N)${NC}"
read -r response
if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
    echo -e "${YELLOW}Restarting backend...${NC}"
    cd backend
    # Kill existing backend process
    pkill -f "python.*main.py" || true
    # Start backend
    python main.py &
    cd ..
    echo -e "${GREEN}✓ Backend restarted${NC}"
fi
echo ""

echo -e "${GREEN}================================${NC}"
echo -e "${GREEN}Integration complete!${NC}"
echo -e "${GREEN}================================${NC}"
echo ""
echo "Next steps:"
echo "  1. Login to SOC Copilot frontend"
echo "  2. Navigate to /wazuh page"
echo "  3. Verify connection to Wazuh stream"
echo ""
echo "Test the integration:"
echo "  - Send a test alert: ./test_wazuh_stream.sh"
echo "  - Check Wazuh Dashboard: https://localhost:5601"
echo ""
