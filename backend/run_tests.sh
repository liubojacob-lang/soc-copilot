#!/bin/bash
# Test runner script with coverage reporting

set -e

echo "🧪 Running SOC Copilot Test Suite"
echo "====================================="

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
elif [ -d ".venv" ]; then
    echo "Activating virtual environment..."
    source .venv/bin/activate
fi

# Install test dependencies
echo "Installing test dependencies..."
pip install pytest pytest-asyncio pytest-cov pytest-mock httpx -q

# Run tests with coverage
echo ""
echo "Running tests with coverage..."
echo ""

pytest \
    --cov=. \
    --cov-report=html \
    --cov-report=term-missing \
    --cov-report=json \
    --verbose \
    --tb=short \
    tests/

# Check exit code
TEST_EXIT_CODE=$?

echo ""
echo "====================================="
if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}✓ All tests passed!${NC}"
    echo ""
    echo "Coverage report generated:"
    echo "  - HTML: htmlcov/index.html"
    echo "  - JSON: coverage.json"
    echo ""
    echo "Open htmlcov/index.html in your browser to view detailed coverage."
else
    echo -e "${RED}✗ Some tests failed${NC}"
    echo ""
    echo "Check the output above for details."
    exit $TEST_EXIT_CODE
fi
