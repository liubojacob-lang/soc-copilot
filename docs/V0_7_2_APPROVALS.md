# SOC Copilot v0.7.2 - Approval System & Notifications

## Version

**v0.7.2** - Human Approval Workflow, Slack Notifications, Run Failure Alerts

---

## What's New in v0.7.2

### 1. Human Approval Nodes

**Pause playbook execution for manual approval**

- **human_approval** node type that pauses execution
- Playbook waits for admin/auditor approval before continuing
- Configurable timeout with auto-reject on expiry
- RBAC: admin/analyst can request, admin/auditor can approve

### 2. Approvals Inbox UI

**Dedicated approval management interface**

- `/playbooks/approvals` page for approval management
- Filter by status (pending, approved, rejected)
- One-click approve/reject with comments
- Real-time auto-refresh for pending approvals
- Direct link to run details

### 3. Slack Webhook Notifications

**Real-time notifications to Slack channels**

- **slack_webhook_notify** node type
- Message templates with variable support
- Beautiful Slack blocks format
- Notification failures don't fail the run

### 4. Run Failure Alerts

**Automatic Slack alerts on playbook failures**

- Configurable via `ENABLE_RUN_FAILURE_NOTIFY` environment variable
- Automatically notifies when runs fail/timeout/cancel
- Includes error details and failed node information

---

## Database Schema Changes

### playbook_approvals Table

```sql
CREATE TABLE playbook_approvals (
    id VARCHAR(36) PRIMARY KEY,
    run_id VARCHAR(36) NOT NULL,
    node_id VARCHAR(100) NOT NULL,
    requested_by_user_id VARCHAR(36),
    approved_by_user_id VARCHAR(36),
    rejected_by_user_id VARCHAR(36),
    status VARCHAR(20) NOT NULL,        -- pending/approved/rejected/expired
    title VARCHAR(200),
    message TEXT,
    comments TEXT,
    timeout_seconds INTEGER,
    on_timeout VARCHAR(20) DEFAULT 'fail', -- approve/reject/fail
    created_at DATETIME NOT NULL,
    decided_at DATETIME,
    expires_at DATETIME,
    FOREIGN KEY (run_id) REFERENCES playbook_runs(id) ON DELETE CASCADE,
    INDEX idx_status (status),
    INDEX idx_run_id (run_id)
);
```

---

## New Node Types

### human_approval

**Pause execution and wait for manual approval**

```json
{
  "id": "approval_step",
  "step_id": "human_approval",
  "name": "Manual Review Required",
  "config": {
    "title": "Security Approval Required",
    "message": "Please review the findings and approve to continue remediation",
    "timeout_seconds": 3600,
    "on_timeout": "fail"
  }
}
```

**Configuration:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| title | string | No | Approval title |
| message | string | No | Detailed message for approvers |
| timeout_seconds | integer | No | Approval timeout in seconds |
| on_timeout | string | No | approve/reject/fail (default: fail) |

### slack_webhook_notify

**Send notifications to Slack channels**

```json
{
  "id": "slack_notify",
  "step_id": "slack_webhook_notify",
  "name": "Notify Slack",
  "config": {
    "webhook_url": "${SLACK_WEBHOOK_DEFAULT}",
    "message_template": "Playbook run {{run_id}} completed with status: {{status}}",
    "include_output_fields": ["risk_score", "threat_level"]
  }
}
```

**Configuration:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| webhook_url | string | No | Slack webhook URL (supports ${ENV_VAR}) |
| message_template | string | No | Message template with variables |
| include_output_fields | array | No | Output fields to include |

**Supported Variables:**
- `{{run_id}}` - Playbook run ID
- `{{status}}` - Current status
- `{{node_id}}` - Current node ID
- Any output field via `include_output_fields`

---

## New API Endpoints

### Approvals Management

| Method | Endpoint | Description | RBAC |
|--------|----------|-------------|------|
| GET | `/api/playbook/approvals` | List approvals with filters | all users |
| POST | `/api/playbook/approvals/{id}/approve` | Approve a request | admin, auditor |
| POST | `/api/playbook/approvals/{id}/reject` | Reject a request | admin, auditor |
| GET | `/api/playbook/approvals/pending/count` | Get pending count | all users |

**RBAC Rules:**
- **admin/auditor**: Can see ALL approvals
- **analyst**: Can only see their OWN approval requests
- **analyst**: CANNOT approve (self-approval prevention)

---

## Environment Variables

### Slack Notifications

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SLACK_WEBHOOK_DEFAULT` | No | - | Default Slack webhook URL for notifications |
| `ENABLE_RUN_FAILURE_NOTIFY` | No | false | Enable automatic failure alerts |

---

## Approval Workflow

### Request Approval Flow

```
1. Analyst starts playbook → human_approval node
2. Node pauses, status = "waiting_approval"
3. Approval record created in database
4. Admin/Auditor receives notification (if configured)
5. Admin/Auditor approves/rejects via API or UI
6. Playbook execution resumes
7. Node completes with approval status
```

### Status Transitions

```
pending → approved → resume execution
pending → rejected → node fails → run may continue or fail
pending → expired → auto-reject based on on_timeout
```

---

## UI Changes

### Approvals Page (`/playbooks/approvals`)

- Real-time approval list with status filtering
- One-click approve/reject actions
- Comment support for approval decisions
- Direct navigation to run details
- Auto-refresh every 10 seconds for pending approvals

### Run Page Enhancements

- **waiting_approval nodes** display with yellow border
- Special icon (🙋) for approval nodes
- Shows approval title, message, and expiration
- "View Approvals Page" button for quick access
- Displays approval history (who approved/rejected, when)

---

## Migration Guide

### From v0.7.1 to v0.7.2

```bash
# Backend - Migration will run automatically on startup
cd backend
python main.py

# Frontend
cd frontend
npm run dev
```

**Migration Details:**
- Adds `playbook_approvals` table
- No breaking changes to existing APIs
- Existing playbooks continue to work
- New node types are optional

---

## API Examples

### 1. List Pending Approvals

```bash
curl -X GET "http://localhost:8000/api/playbook/approvals?status=pending&page=1&page_size=20" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 2. Get All Approvals (Admin/Auditor)

```bash
curl -X GET "http://localhost:8000/api/playbook/approvals" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 3. Get My Approvals (Analyst)

```bash
curl -X GET "http://localhost:8000/api/playbook/approvals" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 4. Approve a Request

```bash
curl -X POST "http://localhost:8000/api/playbook/approvals/{approval_id}/approve" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"comments": "Reviewed and approved remediation plan"}'
```

### 5. Reject a Request

```bash
curl -X POST "http://localhost:8000/api/playbook/approvals/{approval_id}/reject" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"comments": "Insufficient evidence for containment"}'
```

### 6. Get Pending Count

```bash
curl -X GET "http://localhost:8000/api/playbook/approvals/pending/count" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 7. Create Playbook with Human Approval

```bash
curl -X POST "http://localhost:8000/api/playbook/run" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "playbook_name": "phishing_triage",
    "input_json": {
      "alert_subject": "Suspicious email reported",
      "alert_body": "Received from external@unknown.com"
    },
    "mode": "dry_run"
  }'
```

### 8. Get Run Details with Approval Status

```bash
curl -X GET "http://localhost:8000/api/playbook/runs/{run_id}" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 9. Get Run Nodes (including approval nodes)

```bash
curl -X GET "http://localhost:8000/api/playbook/runs/{run_id}/nodes" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 10. Resume Playbook from Approval

```bash
curl -X POST "http://localhost:8000/api/playbook/runs/{run_id}/resume" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "run_mode": "dry_run",
    "from_step_index": 0
  }'
```

### 11. Send Slack Notification (via node)

```bash
# Include in playbook definition
curl -X POST "http://localhost:8000/api/playbook-definitions/{id}/run" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "mode": "dry_run",
    "input_json": {
      "alert_id": "12345"
    }
  }'
```

### 12. Enable Failure Notifications (Environment)

```bash
# Backend .env file
ENABLE_RUN_FAILURE_NOTIFY=true
SLACK_WEBHOOK_DEFAULT=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
```

### 13. Get Available Playbooks

```bash
curl -X GET "http://localhost:8000/api/playbook/playbooks" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 14. Get Run History

```bash
curl -X GET "http://localhost:8000/api/playbook/runs?page=1&page_size=20" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 15. Search Approvals by Date Range

```bash
curl -X GET "http://localhost:8000/api/playbook/approvals?status=pending&page=1&page_size=20" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## Playbook Definition Examples

### Example 1: Simple Approval

```json
{
  "name": "Approval Example",
  "description": "Simple approval required",
  "nodes": [
    {
      "id": "step1",
      "step_id": "extract_iocs",
      "name": "Extract IOCs",
      "config": {}
    },
    {
      "id": "step2",
      "step_id": "human_approval",
      "name": "Security Review",
      "config": {
        "title": "Security Approval Required",
        "message": "Please review the IOCs and approve containment",
        "timeout_seconds": 3600,
        "on_timeout": "reject"
      }
    },
    {
      "id": "step3",
      "step_id": "slack_webhook_notify",
      "name": "Notify Slack",
      "config": {
        "webhook_url": "${SLACK_WEBHOOK_DEFAULT}",
        "message_template": "Approval {{status}} for run {{run_id}}"
      }
    }
  ],
  "edges": [
    {"source": "step1", "target": "step2"},
    {"source": "step2", "target": "step3"}
  ]
}
```

### Example 2: Approval with Slack Notification

```json
{
  "name": "Approval with Notification",
  "description": "Approval with automatic Slack notifications",
  "nodes": [
    {
      "id": "notify1",
      "step_id": "slack_webhook_notify",
      "name": "Notify Pending Approval",
      "config": {
        "webhook_url": "${SLACK_WEBHOOK_DEFAULT}",
        "message_template": "🙋 Approval required for run {{run_id}}",
        "include_output_fields": ["alert_subject"]
      }
    },
    {
      "id": "approve1",
      "step_id": "human_approval",
      "name": "Await Approval",
      "config": {
        "title": "Manual Review Required",
        "message": "Please review and approve to continue",
        "timeout_seconds": 7200
      }
    },
    {
      "id": "notify2",
      "step_id": "slack_webhook_notify",
      "name": "Notify Completion",
      "config": {
        "message_template": "✅ Approved! Run {{run_id}} continuing"
      }
    }
  ],
  "edges": [
    {"source": "notify1", "target": "approve1"},
    {"source": "approve1", "target": "notify2"}
  ]
}
```

---

## Testing Approval Workflow

### 1. Create a Playbook with Approval Node

```bash
# Create definition with approval
curl -X POST "http://localhost:8000/api/playbook-definitions" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d @- << 'EOF'
{
  "name": "Manual Approval Test",
  "description": "Test human approval workflow",
  "nodes": [
    {
      "id": "step1",
      "step_id": "extract_iocs",
      "name": "Extract IOCs",
      "config": {}
    },
    {
      "id": "step2",
      "step_id": "human_approval",
      "name": "Await Approval",
      "config": {
        "title": "Security Review",
        "message": "Please approve to continue",
        "timeout_seconds": 3600
      }
    },
    {
      "id": "step3",
      "step_id": "ti_lookup_otx",
      "name": "TI Lookup",
      "config": {}
    }
  ],
  "edges": [
    {"source": "step1", "target": "step2"},
    {"source": "step2", "target": "step3"}
  ]
}
EOF
```

### 2. Execute the Playbook

```bash
curl -X POST "http://localhost:8000/api/playbook-definitions/{definition_id}/run" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"mode": "dry_run", "input_json": {}}'
```

### 3. Check for Pending Approvals

```bash
curl -X GET "http://localhost:8000/api/playbook/approvals?status=pending" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 4. Approve the Request

```bash
# Get approval_id from step 3, then:
curl -X POST "http://localhost:8000/api/playbook/approvals/{approval_id}/approve" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"comments": "Approved - IOCs verified"}'
```

### 5. Verify Execution Continued

```bash
curl -X GET "http://localhost:8000/api/playbook/runs/{run_id}/nodes" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## RBAC Summary

### Approval Permissions

| Action | Admin | Analyst | Auditor |
|---------|-------|--------|--------|
| View all approvals | ✅ | ❌ | ✅ |
| View own approvals | ✅ | ✅ | ✅ |
| Create approval (run playbook) | ✅ | ✅ | ❌ |
| Approve request | ✅ | ❌ | ✅ |
| Reject request | ✅ | ❌ | ✅ |

### Key Security Rules

1. **Self-approval prevention**: Analysts cannot approve (even their own requests)
2. **Audit logging**: All approval actions logged to `audit_logs` table
3. **Auto-resume**: Approved runs automatically continue execution
4. **Timeout handling**: Expired approvals auto-reject based on `on_timeout` setting

---

## Troubleshooting

### Approval stuck in pending

```bash
# Check if approval exists
curl -X GET "http://localhost:8000/api/playbook/approvals/{approval_id}" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Check run status
curl -X GET "http://localhost:8000/api/playbook/runs/{run_id}" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Slack notifications not working

```bash
# Check environment variables
echo $SLACK_WEBHOOK_DEFAULT
echo $ENABLE_RUN_FAILURE_NOTIFY

# Test webhook URL
curl -X POST YOUR_WEBHOOK_URL \
  -H "Content-Type: application/json" \
  -d '{"text": "Test notification"}'
```

### Node not resuming after approval

```bash
# Check node status
curl -X GET "http://localhost:8000/api/playbook/runs/{run_id}/nodes" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Check for errors in backend logs
# Backend should show "Resuming from approval" message
```

---

## Migration Rollback

If needed, rollback to v0.7.1:

```bash
cd backend
alembic downgrade v0_7_2_approval_system
```

This will:
- Drop `playbook_approvals` table
- Remove approval-related indexes
- Keep all other v0.7.1 functionality intact

---

## Changelog

### v0.7.2 (2026-02-09)

**Added:**
- Human approval nodes with timeout support
- Approvals management UI at `/playbooks/approvals`
- Slack webhook notification nodes
- Automatic run failure alerts
- Approval API endpoints (approve, reject, list)
- `playbook_approvals` database table
- Enhanced run page with approval status display

**Changed:**
- Playbook execution engine to handle `waiting_approval` state
- Node status display with approval indicators
- RBAC rules for approval operations

**Fixed:**
- Resume functionality after approval
- Proper audit logging for approval actions
- Notification error handling (non-blocking)

---

## Documentation Links

- [API Documentation](http://localhost:8000/docs)
- [OpenAPI Specification](./openapi.json)
- [Test Cases](./TEST_CASES.md)
- [Manual Test Guide](./MANUAL_TEST_GUIDE.md)
