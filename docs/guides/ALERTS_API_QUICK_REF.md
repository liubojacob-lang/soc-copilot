# 🔔 Security Alerts API - Quick Reference

**Base URL**: `http://localhost:8000/api/v1/security-alerts`

---

## 📝 Quick Start

### 1. Test Ingest Alert

```bash
curl -X POST http://localhost:8000/api/v1/security-alerts/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "source": "wazuh",
    "event_id": "test-001",
    "timestamp": "2026-02-24T10:00:00Z",
    "event_type": "web_attack",
    "severity": "high",
    "title": "SQL Injection Attempt",
    "description": "SQL injection detected",
    "source_ip": "192.168.1.100",
    "rule_id": "31101",
    "rule_groups": ["web"],
    "rule_mitre": ["TA0001"]
  }'
```

### 2. List Alerts

```bash
# All alerts
curl http://localhost:8000/api/v1/security-alerts/

# Filter by severity
curl "http://localhost:8000/api/v1/security-alerts/?severity=high"

# Filter by status
curl "http://localhost:8000/api/v1/security-alerts/?status=open"

# Search in title/description
curl "http://localhost:8000/api/v1/security-alerts/?search=sql"
```

### 3. Get Statistics

```bash
curl http://localhost:8000/api/v1/security-alerts/stats/summary
```

---

## 🔧 Endpoints

| Method | Endpoint         | Description                      |
| ------ | ---------------- | -------------------------------- |
| POST   | `/ingest`        | Receive alert from external tool |
| GET    | `/`              | List alerts with filters         |
| GET    | `/{id}`          | Get alert details                |
| PATCH  | `/{id}`          | Update alert status              |
| DELETE | `/{id}`          | Delete alert                     |
| GET    | `/stats/summary` | Alert statistics                 |

---

## 🎛️ Query Parameters

**For GET /api/v1/security-alerts/**

| Parameter    | Type   | Example      | Description              |
| ------------ | ------ | ------------ | ------------------------ |
| `source`     | string | `wazuh`      | Filter by source         |
| `severity`   | string | `high`       | Filter by severity       |
| `status`     | string | `open`       | Filter by status         |
| `agent_name` | string | `web-01`     | Filter by agent          |
| `source_ip`  | string | `1.2.3.4`    | Filter by IP             |
| `event_type` | string | `web_attack` | Filter by type           |
| `search`     | string | `sql`        | Search text              |
| `page`       | int    | `1`          | Page number              |
| `page_size`  | int    | `50`         | Items per page (max 100) |

---

## 📊 Severity Levels

```
critical  - Immediate action required
high      - Urgent investigation needed
medium    - Investigate soon
low       - Low priority
info      - Informational only
```

## 🔄 Status Values

```
open           - New alert, not investigated
investigating  - Analyst is investigating
closed         - Resolved/confirmed threat
false_positive - Not a real threat
```

## 🏷️ Sources

```
wazuh    - Wazuh SIEM
snort    - Snort IDS
osquery  - OSQuery EDR
suricata - Suricata IDS
custom   - Custom source
```

---

## 💡 Response Examples

### Ingest Response

```json
{
  "status": "success",
  "message": "Alert ingested successfully",
  "alert_id": 1
}
```

### List Response

```json
{
  "total": 150,
  "alerts": [
    {
      "id": 1,
      "source": "wazuh",
      "title": "SQL Injection Attempt",
      "severity": "high",
      "status": "open",
      "created_at": "2026-02-24T10:00:00Z"
    }
  ],
  "page": 1,
  "page_size": 50
}
```

### Statistics Response

```json
{
  "total": 150,
  "by_severity": { "critical": 5, "high": 25 },
  "by_status": { "open": 80, "investigating": 20 },
  "by_source": { "wazuh": 100, "snort": 30 },
  "last_24h": 15,
  "last_7d": 75,
  "last_30d": 150
}
```

---

## 🔗 MITRE ATT&CK Tactics

Common tactics to include in `rule_mitre`:

```
TA0001 - Initial Access
TA0002 - Execution
TA0003 - Persistence
TA0004 - Privilege Escalation
TA0005 - Defense Evasion
TA0006 - Credential Access
TA0007 - Discovery
TA0008 - Lateral Movement
TA0009 - Collection
TA0010 - Exfiltration
TA0011 - Command and Control
TA0040 - Impact
```

---

## 🧪 Testing

```bash
# Test with Python script
cd backend
python test_security_alerts.py

# View API docs
open http://localhost:8000/docs

# Check database
sqlite3 sec_copilot.db "SELECT COUNT(*) FROM security_alerts;"
```

---

## 📚 Full Docs

- [Integration Summary](./INTEGRATION_SUMMARY.md)
- [Complete Guide](./INTEGRATION_COMPLETE.md)
- [Integration Plan](./SECURITY_INTEGRATION_PLAN.md)
