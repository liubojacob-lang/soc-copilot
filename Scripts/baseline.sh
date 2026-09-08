#!/usr/bin/env bash
# SOC Copilot baseline collection script
# Run this script before/after optimization phases to track progress.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
DATE_STR="$(date +%Y%m%d)"
REPORT_DIR="$ROOT_DIR/docs/baselines"
REPORT_FILE="$REPORT_DIR/BASELINE_${DATE_STR}.md"

mkdir -p "$REPORT_DIR"

echo "Collecting SOC Copilot baseline metrics..."

cd "$ROOT_DIR"

# Backend tests + coverage
BACKEND_TEST_LOG="$(mktemp)"
(
  cd "$ROOT_DIR/backend"
  pytest --cov=. --cov-report=term-missing --tb=short -q 2>&1 | tee "$BACKEND_TEST_LOG" || true
) || true

BACKEND_COVERAGE="$(grep -oE 'Required test coverage[^%]+%' "$BACKEND_TEST_LOG" | grep -oE '[0-9]+\.[0-9]+%' | tail -1 || echo 'N/A')"
BACKEND_RESULT="$(grep -oE '[0-9]+ passed, [0-9]+ failed, [0-9]+ skipped' "$BACKEND_TEST_LOG" | tail -1 || echo 'N/A')"

# Frontend tests + coverage
FRONTEND_TEST_LOG="$(mktemp)"
(
  cd "$ROOT_DIR/frontend"
  npm run test:coverage 2>&1 | tee "$FRONTEND_TEST_LOG" || true
) || true

FRONTEND_RESULT="$(grep -oE 'Test Files[[:space:]]+[0-9]+ passed' "$FRONTEND_TEST_LOG" | tail -1 || echo 'N/A')"
FRONTEND_COVERAGE="$(grep -oE 'All files \|.*\|' "$FRONTEND_TEST_LOG" | tail -1 | awk -F'|' '{print $2}' | tr -d ' ' || echo 'N/A')"

# Backend startup time
STARTUP_LOG="$(mktemp)"
START_TIME="$(date +%s.%N)"
python3 - "$ROOT_DIR" "$STARTUP_LOG" <<'PY' &
import sys, subprocess, select, time
root_dir, log_path = sys.argv[1], sys.argv[2]
with open(log_path, 'w') as f:
    proc = subprocess.Popen(
        [sys.executable, '-m', 'uvicorn', 'backend.main:app', '--host', '127.0.0.1', '--port', '8000'],
        cwd=root_dir,
        stdout=f,
        stderr=subprocess.STDOUT,
        text=True,
    )
    start = time.time()
    ready = False
    while time.time() - start < 30:
        readable, _, _ = select.select([proc.stdout], [], [], 0.5)
        if readable:
            line = proc.stdout.readline()
            f.write(line)
            f.flush()
            if 'Application startup complete' in line or 'Uvicorn running' in line:
                ready = True
                break
        if proc.poll() is not None:
            break
    proc.terminate()
    try:
        proc.wait(timeout=3)
    except:
        proc.kill()
PY
UVICORN_PID=$!
wait $UVICORN_PID || true
END_TIME="$(date +%s.%N)"
STARTUP_SECONDS="$(echo "$END_TIME - $START_TIME" | bc)"

# Frontend build
FRONTEND_BUILD_LOG="$(mktemp)"
(
  cd "$ROOT_DIR/frontend"
  npm run build 2>&1 | tee "$FRONTEND_BUILD_LOG" || true
) || true

if grep -q "Build successful\|Compiled successfully" "$FRONTEND_BUILD_LOG"; then
  BUILD_STATUS="success"
  FIRST_SCREEN_JS="$(find "$ROOT_DIR/frontend/.next/static/chunks" -name '*.js' -type f -exec wc -c {} + 2>/dev/null | sort -n | tail -1 | awk '{print $1}' || echo 'N/A')"
else
  BUILD_STATUS="failed"
  FIRST_SCREEN_JS="N/A"
fi

# Write report
cat > "$REPORT_FILE" <<EOF
# SOC Copilot Baseline Report — ${DATE_STR}

## Test Coverage

### Backend

- Result: ${BACKEND_RESULT}
- Coverage: ${BACKEND_COVERAGE}

### Frontend

- Result: ${FRONTEND_RESULT}
- Coverage: ${FRONTEND_COVERAGE}

## Performance

- Backend startup time: ${STARTUP_SECONDS}s
- Frontend build: ${BUILD_STATUS}
- First-screen JS size (bytes): ${FIRST_SCREEN_JS}

## Notes

- Logs captured during this run are not persisted; inspect terminal output for details.
- Update the coverage targets in the roadmap as metrics improve.
EOF

echo "Baseline report written to: $REPORT_FILE"
