# Phase 3: Advanced Analytics Features

## 🎯 Overview

Phase 3 introduces advanced security analytics capabilities including UEBA (User and Entity Behavior Analytics), proactive threat hunting, and enhanced threat intelligence.

## ✨ New Features

### 1. UEBA (User and Entity Behavior Analytics)

**File**: `backend/services/ueba_service.py`

User and Entity Behavior Analytics system that detects insider threats and anomalous behavior using ML.

**Key Capabilities**:

- **Behavior Baseline Building**: Learns normal behavior patterns for users, hosts, and IPs
- **Anomaly Detection**: Identifies deviations from baseline
  - Unusual login times
  - Abnormal data access volumes
  - Lateral movement patterns
  - Off-hours activity
- **Risk Scoring**: Calculates overall risk scores (0-100)
- **ML-based Detection**: Uses Isolation Forest for unsupervised anomaly detection
- **Peer Group Analysis**: Compares behavior against peer groups

**API Endpoints**:

```
POST   /api/ueba/detect              - Detect behavioral anomalies
GET    /api/ueba/risk-profile/{id}   - Get user risk profile
POST   /api/ueba/build-baseline      - Build behavior baseline
GET    /api/ueba/high-risk-users     - Get high-risk user list
GET    /api/ueba/dashboard           - Get UEBA dashboard
```

**Example Usage**:

```bash
# Detect anomalies for a user
curl -X POST http://localhost:8000/api/ueba/detect \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "entity_id": "user_001",
    "entity_type": "user",
    "login_time": "2024-01-15T02:30:00",
    "data_volume_mb": 500,
    "accessed_hosts": ["server1", "server2", "server3"]
  }'

# Get user risk profile
curl http://localhost:8000/api/ueba/risk-profile/user_001 \
  -H "Authorization: Bearer $TOKEN"
```

### 2. Threat Hunting

**File**: `backend/services/threat_hunting_service.py`

Proactive threat discovery platform for hypothesis-driven hunting.

**Key Capabilities**:

- **Hypothesis-Driven Hunting**: Based on MITRE ATT&CK framework
  - Lateral Movement Detection
  - PowerShell Obfuscation
  - Persistence via Scheduled Tasks
  - Data Exfiltration via DNS
  - Kerberoasting Activity
- **IOC Hunting**: Search for known indicators of compromise
- **Custom Hypotheses**: Create custom hunting rules
- **Automated Execution**: Run hunts against historical data

**Built-in Hunt Hypotheses**:

| ID       | Name                            | MITRE Technique  | Severity |
| -------- | ------------------------------- | ---------------- | -------- |
| hunt_001 | Lateral Movement via SMB        | T1021.002        | High     |
| hunt_002 | PowerShell Obfuscation          | T1059.001, T1027 | Critical |
| hunt_003 | Persistence via Scheduled Tasks | T1053.005        | High     |
| hunt_004 | Data Exfiltration via DNS       | T1071.004        | Medium   |
| hunt_005 | Kerberoasting Activity          | T1558.003        | Critical |

**API Endpoints**:

```
GET    /api/threat-hunting/hypotheses      - List hunt hypotheses
POST   /api/threat-hunting/hypotheses      - Create custom hypothesis
POST   /api/threat-hunting/execute         - Execute hunt
POST   /api/threat-hunting/ioc-hunt        - Hunt for IOCs
GET    /api/threat-hunting/results         - Get hunt results
GET    /api/threat-hunting/dashboard       - Get hunting dashboard
```

**Example Usage**:

```bash
# List available hypotheses
curl http://localhost:8000/api/threat-hunting/hypotheses \
  -H "Authorization: Bearer $TOKEN"

# Execute a hunt
curl -X POST http://localhost:8000/api/threat-hunting/execute \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "hypothesis_id": "hunt_002",
    "time_range_hours": 24
  }'

# Hunt for IOCs
curl -X POST http://localhost:8000/api/threat-hunting/ioc-hunt \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "iocs": [
      {"type": "ip", "value": "192.168.1.100"},
      {"type": "domain", "value": "evil.com"}
    ],
    "time_range_days": 30
  }'
```

### 3. Enhanced Threat Intelligence

**Upgrade to existing threat_intel service**

Planned enhancements (not yet implemented):

- Multi-source aggregation (VirusTotal, MISP, Abuse.ch)
- STIX/TAXII support
- Intelligence correlation
- Automated IOC extraction from alerts

## 🔧 Architecture

### UEBA Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     UEBA Engine                              │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌─────────────────┐   │
│  │   Baseline   │  │    Anomaly   │  │  Risk Scoring   │   │
│  │   Builder    │→ │  Detection   │→ │    Engine       │   │
│  └──────────────┘  └──────────────┘  └─────────────────┘   │
│         ↑                                    ↓              │
│         │                            ┌──────────────┐      │
│         └────────────────────────────┤  ML Models   │      │
│                                      │(Isolation    │      │
│                                      │  Forest)     │      │
│                                      └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
```

### Threat Hunting Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                  Threat Hunting Engine                       │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │   Hypothesis │    │    Hunt      │    │   Findings   │  │
│  │   Library    │───→│  Execution   │───→│   Analysis   │  │
│  │(MITRE-based) │    │              │    │              │  │
│  └──────────────┘    └──────────────┘    └──────────────┘  │
│         ↑                  ↓                   ↓             │
│         │           ┌──────────────┐    ┌──────────────┐    │
│         └───────────┤  Data Store  │    │  IOC Hunt    │    │
│                     └──────────────┘    └──────────────┘    │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## 📊 Data Models

### UEBA Models

**BehaviorBaseline**:

```python
{
  "entity_id": "user_001",
  "entity_type": "user",
  "login_times": [9, 10, 11, 14, 15, 16],
  "accessed_resources": ["file_share", "email"],
  "typical_data_volume": 100.0,
  "typical_connections": 10
}
```

**AnomalyDetection**:

```python
{
  "entity_id": "user_001",
  "behavior_type": "login",
  "anomaly_score": 0.85,
  "risk_level": "high",
  "description": "Login at unusual hour: 02:00",
  "indicators": ["off_hours_login"],
  "recommended_actions": ["verify_identity"]
}
```

### Threat Hunting Models

**HuntHypothesis**:

```python
{
  "id": "hunt_001",
  "name": "Lateral Movement via SMB",
  "mitre_techniques": ["T1021.002"],
  "data_sources": ["network_traffic"],
  "query_logic": "SELECT * FROM smb_events...",
  "severity": "high"
}
```

**HuntFinding**:

```python
{
  "id": "finding_001",
  "entity_type": "host",
  "entity_id": "workstation-001",
  "confidence": 0.92,
  "severity": "critical",
  "evidence": {...}
}
```

## 🚀 Getting Started

### 1. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 2. Start the Server

```bash
python -m uvicorn main:app --reload
```

### 3. Access API Documentation

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### 4. Test the APIs

Use the provided example curl commands or access the interactive documentation.

## 📈 Performance Considerations

### UEBA

- Baseline building: Run periodically (e.g., weekly)
- Real-time anomaly detection: < 100ms per query
- ML model training: Background job

### Threat Hunting

- Hunt execution: Depends on data volume (seconds to minutes)
- IOC hunting: Optimized for large-scale searches
- Results caching: Cache hunt results for 1 hour

## 🔐 Security Considerations

- All UEBA endpoints require authentication
- Threat hunting results may contain sensitive data
- Hypothesis queries should be validated to prevent injection
- Risk scores should trigger appropriate alerts

## 📝 Future Enhancements

### UEBA

- [ ] Graph-based relationship analysis
- [ ] Time-series anomaly detection
- [ ] Integration with SIEM data sources
- [ ] Automated playbook triggering

### Threat Hunting

- [ ] Jupyter notebook integration
- [ ] Hunt scheduling (cron-based)
- [ ] Machine learning hunt suggestions
- [ ] Collaborative hunt notebooks

## 🔗 Integration Points

- **Alerts**: UEBA anomalies create alerts
- **Playbooks**: Hunt findings can trigger playbook execution
- **Threat Intel**: IOC hunts integrate with threat intelligence
- **AI Copilot**: Natural language hunting queries

---

**Next Steps**: Phase 4 - Ecosystem & Cloud Native Features
