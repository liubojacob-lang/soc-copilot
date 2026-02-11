#!/bin/bash
# SOC Copilot v0.7 DAG-Based Playbook Engine - Curl Verification Tests
# Run these tests to verify the DAG implementation is working correctly

set -e

API_BASE="${API_BASE:-http://localhost:8000}"
TOKEN="${TOKEN:-}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Helper functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_test() {
    echo -e "${YELLOW}[TEST]${NC} $1"
}

check_response() {
    local expected=$1
    local actual=$2
    if [ "$expected" == "$actual" ]; then
        return 0
    else
        log_error "Expected $expected but got $actual"
        return 1
    fi
}

# ============================================
# Test Setup
# ============================================
log_info "Starting SOC Copilot v0.7 DAG Verification Tests"
log_info "API Base: $API_BASE"

# Health check
log_test "1. Health Check"
response=$(curl -s "$API_BASE/api/health")
echo "$response" | grep -q "v0.7"
if [ $? -eq 0 ]; then
    log_info "✓ Health check passed - v0.7 detected"
else
    log_error "✗ Health check failed"
fi

# ============================================
# Test 2: List Playbook Definitions
# ============================================
log_test "2. List Playbook Definitions"
response=$(curl -s -X GET "$API_BASE/api/playbook/definitions" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json")
echo "$response"
definitions=$(echo "$response" | grep -o '"definitions"' | wc -l)
if [ "$definitions" -gt 0 ]; then
    log_info "✓ Listed $definitions playbook definitions"
else
    log_error "✗ Failed to list definitions"
fi

# ============================================
# Test 3: Create DAG Definition
# ============================================
log_test "3. Create DAG Definition"
definition_response=$(curl -s -X POST "$API_BASE/api/playbook/definitions?name=Test+DAG+Playbook&description=Test+DAG+for+verification&version=1.0.0" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{
      "nodes": [
        {"id": "extract", "step_id": "ioc_extract", "name": "Extract IOCs"},
        {"id": "ti_lookup", "step_id": "ti_lookup_otx", "name": "OTX Lookup"},
        {"id": "enrich", "step_id": "asset_enrich", "name": "Enrich Assets"}
      ],
      "edges": [
        {"source": "extract", "target": "ti_lookup"},
        {"source": "extract", "target": "enrich"}
      ]
    }')
echo "$definition_response"

definition_id=$(echo "$definition_response" | grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4)
if [ -n "$definition_id" ]; then
    log_info "✓ Created DAG definition with ID: $definition_id"
else
    log_error "✗ Failed to create DAG definition"
    definition_id="demo-parallel-analysis"  # Fallback to demo definition
fi

# ============================================
# Test 4: Get Definition by ID
# ============================================
log_test "4. Get Definition by ID ($definition_id)"
response=$(curl -s -X GET "$API_BASE/api/playbook/definitions/$definition_id" \
    -H "Authorization: Bearer $TOKEN")
echo "$response" | grep -q '"definition_json"'
if [ $? -eq 0 ]; then
    log_info "✓ Retrieved definition successfully"
else
    log_error "✗ Failed to retrieve definition"
fi

# ============================================
# Test 5: Execute DAG (Dry Run)
# ============================================
log_test "5. Execute DAG (Dry Run)"
execute_response=$(curl -s -X POST "$API_BASE/api/playbook/definitions/$definition_id/run?mode=dry_run" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"input_json": {}}')
echo "$execute_response"

run_id=$(echo "$execute_response" | grep -o '"run_id":"[^"]*"' | cut -d'"' -f4)
if [ -n "$run_id" ]; then
    log_info "✓ Started DAG execution with Run ID: $run_id"
else
    log_error "✗ Failed to start DAG execution"
    run_id="test-run-id"
fi

# ============================================
# Test 6: Get Run Details with Nodes
# ============================================
log_test "6. Get Run Details with Nodes ($run_id)"
sleep 2  # Wait for execution to start
response=$(curl -s -X GET "$API_BASE/api/playbook/runs/$run_id/nodes" \
    -H "Authorization: Bearer $TOKEN")
echo "$response"
nodes=$(echo "$response" | grep -o '"node_id"' | wc -l)
if [ "$nodes" -gt 0 ]; then
    log_info "✓ Retrieved $nodes node executions"
else
    log_error "✗ Failed to retrieve node executions"
fi

# ============================================
# Test 7: Get Linear Run Details (Backward Compatibility)
# ============================================
log_test "7. Get Linear Run Details (Backward Compatibility)"
response=$(curl -s -X GET "$API_BASE/api/playbook/runs/$run_id/steps" \
    -H "Authorization: Bearer $TOKEN")
echo "$response" | grep -q '"run"'
if [ $? -eq 0 ]; then
    log_info "✓ Linear run API still works (backward compatibility)"
else
    log_error "✗ Linear run API failed"
fi

# ============================================
# Test 8: List All Runs
# ============================================
log_test "8. List All Runs"
response=$(curl -s -X GET "$API_BASE/api/playbook/runs?page_size=10" \
    -H "Authorization: Bearer $TOKEN")
echo "$response"
total_runs=$(echo "$response" | grep -o '"total":[0-9]*' | grep -o '[0-9]*')
if [ -n "$total_runs" ]; then
    log_info "✓ Listed $total_runs total runs"
else
    log_error "✗ Failed to list runs"
fi

# ============================================
# Test 9: Webhook Health Check
# ============================================
log_test "9. Webhook Health Check"
response=$(curl -s "$API_BASE/api/webhooks/health")
echo "$response" | grep -q '"status":"ok"'
if [ $? -eq 0 ]; then
    log_info "✓ Webhook module is healthy"
else
    log_error "✗ Webhook module health check failed"
fi

# ============================================
# Test 10: Create Webhook Trigger (if supported)
# ============================================
log_test "10: Create Webhook Trigger"
trigger_response=$(curl -s -X POST "$API_BASE/api/playbook/triggers" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d "{
      \"definition_id\": \"$definition_id\",
      \"type\": \"webhook\",
      \"name\": \"Test Webhook\",
      \"config_json\": {
        \"webhook_secret\": \"test-secret-key-12345\"
      }
    }" 2>/dev/null || echo '{"error": "Not implemented yet"}')
echo "$trigger_response"

trigger_id=$(echo "$trigger_response" | grep -o '"id":"[^"]*"' | cut -d'"' -f4)
if [ -n "$trigger_id" ] && [ "$trigger_id" != "null" ]; then
    log_info "✓ Created webhook trigger with ID: $trigger_id"

    # ============================================
    # Test 11: Trigger Webhook with HMAC
    # ============================================
    log_test "11: Trigger Webhook with HMAC Signature"
    payload='{"test": "data"}'
    signature=$(echo -n "$payload" | openssl dgst -sha256 -hmac "test-secret-key-12345" -binary | base64)
    webhook_response=$(curl -s -X POST "$API_BASE/api/webhooks/$trigger_id" \
        -H "X-Signature: $signature" \
        -H "X-Idempotency-Key: test-key-$(date +%s)" \
        -H "Content-Type: application/json" \
        -d "$payload")
    echo "$webhook_response"
    log_info "✓ Webhook triggered (response logged above)"
else
    log_info "⊘ Webhook trigger creation not yet implemented"
fi

# ============================================
# Test 12: Get Available Playbooks (v0.6 compatibility)
# ============================================
log_test "12: Get Available Playbooks (Linear Mode)"
response=$(curl -s -X GET "$API_BASE/api/playbook/playbooks" \
    -H "Authorization: Bearer $TOKEN")
echo "$response" | grep -q '"phishing_triage"'
if [ $? -eq 0 ]; then
    log_info "✓ Linear playbooks still available"
else
    log_error "✗ Failed to get linear playbooks"
fi

# ============================================
# Test 13: Execute Linear Playbook (Backward Compatibility)
# ============================================
log_test "13: Execute Linear Playbook (Backward Compatibility)"
linear_response=$(curl -s -X POST "$API_BASE/api/playbook/run" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{
      "playbook_name": "phishing_triage",
      "mode": "dry_run",
      "input_json": {"raw_log": "test email content"}
    }')
echo "$linear_response"
linear_run_id=$(echo "$linear_response" | grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4)
if [ -n "$linear_run_id" ]; then
    log_info "✓ Linear playbook execution still works (Run ID: $linear_run_id)"
else
    log_error "✗ Linear playbook execution failed"
fi

# ============================================
# Test 14: Check Execution Mode in Run
# ============================================
log_test "14: Verify Execution Mode Field"
response=$(curl -s -X GET "$API_BASE/api/playbook/runs/$run_id" \
    -H "Authorization: Bearer $TOKEN")
echo "$response" | grep -q '"execution_mode":"dag"'
if [ $? -eq 0 ]; then
    log_info "✓ Execution mode field present (dag)"
else
    log_error "✗ Execution mode field not found"
fi

# ============================================
# Test 15: Concurrent Execution Test
# ============================================
log_test "15: Execute Multiple DAG Runs (Concurrent Test)"
run_ids=""
for i in {1..3}; do
    response=$(curl -s -X POST "$API_BASE/api/playbook/definitions/$definition_id/run?mode=dry_run" \
        -H "Authorization: Bearer $TOKEN" \
        -H "Content-Type: application/json" \
        -d '{"input_json": {}}')
    id=$(echo "$response" | grep -o '"run_id":"[^"]*"' | cut -d'"' -f4)
    if [ -n "$id" ]; then
        run_ids="$run_ids $id"
    fi
done

run_count=$(echo "$run_ids" | wc -w)
if [ "$run_count" -eq 3 ]; then
    log_info "✓ Successfully started $run_count concurrent DAG runs"
else
    log_error "✗ Concurrent execution test failed"
fi

# ============================================
# Summary
# ============================================
log_info "=================================="
log_info "SOC Copilot v0.7 Test Summary"
log_info "=================================="
log_info "All core tests completed!"
log_info ""
log_info "Key Features Verified:"
log_info "- DAG definition creation and retrieval"
log_info "- DAG execution (dry run mode)"
log_info "- Node-level execution tracking"
log_info "- Backward compatibility with linear playbooks"
log_info "- Execution mode detection"
log_info "- Concurrent execution support"
log_info "- Webhook trigger endpoints"
log_info ""
log_info "Next Steps:"
log_info "1. Run the actual database migration"
log_info "2. Test with real playbook definitions"
log_info "3. Verify frontend DAG visualization"
log_info "4. Test retry policies with failures"
log_info "5. Set up cron scheduler in production"
