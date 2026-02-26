#!/bin/bash
# Start SOC Copilot Backend with Wazuh Integration
# Development mode - runs directly with Python

set -e

echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║          SOC Copilot Backend - Development Mode                  ║"
echo "║              with Wazuh SIEM Integration                         ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

# Change to backend directory
cd backend

print_info "Starting backend server..."
echo ""
print_warning "Press Ctrl+C to stop the server"
echo ""

# Run the backend with uvicorn
python -m uvicorn main:app \
    --host 0.0.0.0 \
    --port 8001 \
    --reload \
    --log-level info
