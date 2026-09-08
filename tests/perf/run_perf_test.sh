#!/usr/bin/env bash
# Performance testing execution script for SOC Copilot PRR
set -e

HOST=${1:-http://localhost:8000}
USERS=${2:-200}
SPAWN_RATE=${3:-20}
RUN_TIME=${4:-5m}
REPORT_HTML="tests/perf/perf_report_$(date +%Y%m%d_%H%M%S).html"

echo "==================================================="
echo " Starting SOC Copilot Production Load Test"
echo " Target Host: $HOST"
echo " Concurrency: $USERS users (Spawn rate: $SPAWN_RATE/s)"
echo " Duration:    $RUN_TIME"
echo " HTML Report: $REPORT_HTML"
echo "==================================================="

if ! command -v locust &> /dev/null; then
    echo "Locust not found in PATH, installing via pip in venv..."
    ./venv/bin/pip install locust
    LOCUST_BIN="./venv/bin/locust"
else
    LOCUST_BIN="locust"
fi

$LOCUST_BIN -f tests/perf/locustfile.py     --headless     --host="$HOST"     -u "$USERS"     -r "$SPAWN_RATE"     --run-time="$RUN_TIME"     --html="$REPORT_HTML"     --exit-code-on-error 1

echo "Load test complete. Report saved to $REPORT_HTML"
