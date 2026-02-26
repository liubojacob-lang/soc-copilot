#!/bin/bash

# E2E Test Runner Script
# P3-9: E2E测试实现

set -e

echo "🎭 Starting E2E Tests..."

# Check if backend is running
echo "🔍 Checking backend..."
if ! curl -s http://localhost:8000/api/health > /dev/null; then
    echo "❌ Backend is not running on http://localhost:8000"
    echo "Please start the backend first:"
    echo "  cd backend && python start_server.py"
    exit 1
fi

echo "✅ Backend is running"

# Check if frontend is running
echo "🔍 Checking frontend..."
if ! curl -s http://localhost:3003 > /dev/null; then
    echo "⚠️ Frontend is not running on http://localhost:3003"
    echo "Starting frontend dev server..."
    cd frontend
    npm run dev -H localhost -p 3003 &
    FRONTEND_PID=$!
    cd ..

    # Wait for frontend to start
    echo "⏳ Waiting for frontend to start..."
    sleep 10

    # Check again
    if ! curl -s http://localhost:3003 > /dev/null; then
        echo "❌ Frontend failed to start"
        exit 1
    fi

    echo "✅ Frontend started (PID: $FRONTEND_PID)"
else
    echo "✅ Frontend is running"
    FRONTEND_PID=""
fi

# Set environment variables
export E2E_BASE_URL=http://localhost:3003
export CI=${CI:-false}

# Run tests
echo "🚀 Running Playwright E2E tests..."
cd frontend

if [ "$1" = "--ui" ]; then
    npm run test:e2e:ui
elif [ "$1" = "--debug" ]; then
    npm run test:e2e:debug
elif [ "$1" = "--grep" ]; then
    npx playwright test --grep "$2"
else
    npm run test:e2e
fi

TEST_RESULT=$?

# Cleanup
if [ -n "$FRONTEND_PID" ]; then
    echo "🧹 Cleaning up frontend server..."
    kill $FRONTEND_PID 2>/dev/null || true
fi

# Show report
if [ $TEST_RESULT -eq 0 ] && [ "$CI" != "true" ]; then
    echo ""
    echo "📊 Opening test report..."
    npm run test:e2e:report
fi

exit $TEST_RESULT
