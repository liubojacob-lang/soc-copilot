#!/usr/bin/env bash
set -e
ROOT=$(pwd)
echo "[Release] Building widget and demo app..."
cd ai-assistant-widget
npm install --silent
npm run build
cd ../ai-assistant-demo-app
npm install --silent
npm run start &
PID=$!
echo "Demo server started (PID=$PID)"
cd "$ROOT"
