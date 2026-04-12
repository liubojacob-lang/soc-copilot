# Wazuh SIEM Integration Guide

**Version**: v1.0.0
**Last Updated**: 2026-02-24

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Prerequisites](#prerequisites)
4. [Installation](#installation)
5. [Configuration](#configuration)
6. [API Reference](#api-reference)
7. [Testing](#testing)
8. [Troubleshooting](#troubleshooting)
9. [Performance Tuning](#performance-tuning)

---

## Overview

The Wazuh SIEM integration enables SOC Copilot to receive real-time security events from Wazuh, automatically enrich them with threat intelligence, and send notifications through multiple channels (Feishu, Slack, Email).

### Key Features

- ✅ **Real-time log collection** - Polls Wazuh API every 30 seconds (configurable)
- ✅ **Automatic alert mapping** - Converts Wazuh alerts to SOC Copilot format
- ✅ **Severity mapping** - Maps Wazuh rule levels (0-15) to SOC severity (low/medium/high/critical)
- ✅ **MITRE ATT&CK enrichment** - Extracts MITRE techniques from Wazuh rules
- ✅ **Priority queues** - Routes alerts to appropriate priority queues for processing
- ✅ **Multi-channel notifications** - Sends alerts to Feishu, Slack, and Email

### Severity Mapping

| Wazuh Rule Level | SOC Severity | Queue Priority | Response Time   |
| ---------------- | ------------ | -------------- | --------------- |
| 0-3              | Low          | Low            | Within 24 hours |
| 4-7              | Medium       | Medium         | Within 8 hours  |
| 8-12             | High         | High           | Within 1 hour   |
| 13-15            | Critical     | Critical       | Immediate       |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Wazuh SIEM                                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐          │
│  │ Agent 1  │  │ Agent 2  │  │ Agent 3  │  │ Agent N  │          │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘          │
│       └──────────────┴──────────────┴──────────────┴──────────┐    │
│                                     │                           │
│                           ┌─────────▼─────────┐                 │
│                           │   Wazuh Manager   │                 │
│                           │   (API Server)    │                 │
│                           └─────────┬─────────┘                 │
│                                     │                           │
└─────────────────────────────────────┼───────────────────────────┘
                                      │
                                      │ HTTPS (JWT Auth)
                                      │
┌─────────────────────────────────────▼───────────────────────────┐
│                      SOC Copilot                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Wazuh Log Receiver Service                             │   │
│  │  • Polls Wazuh API every 30 seconds                     │   │
│  │  • Fetches new alerts                                   │   │
│  │  • Maintains last poll timestamp                        │   │
│  └────────────────────┬────────────────────────────────────┘   │
│                       │                                          │
│                       ▼                                          │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Wazuh Alert Mapper                                     │   │
│  │  • Converts Wazuh format to SOC format                  │   │
│  │  • Maps severity                                        │   │
│  │  • Extracts MITRE ATT&CK                                │   │
│  │  • Enriches with context                                │   │
│  └────────────────────┬────────────────────────────────────┘   │
│                       │                                          │
│                       ▼                                          │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Redis Streams Message Queue                            │   │
│  │  • Critical Queue (high priority)                       │   │
│  │  • High Queue                                           │   │
│  │  • Medium Queue                                         │   │
│  │  • Low Queue                                            │   │
│  └────────────────────┬────────────────────────────────────┘   │
│                       │                                          │
│                       ▼                                          │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Alert Worker (3 replicas)                              │   │
│  │  • Consumes alerts from queues                          │   │
│  │  • Sends notifications                                  │   │
│  │  • Updates database                                     │   │
│  └────────────────────┬────────────────────────────────────┘   │
│                       │                                          │
│                       ▼                                          │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Notification Service                                   │   │
│  │  • Feishu (interactive cards)                           │   │
│  │  • Slack (rich attachments)                             │   │
│  │  • Email (HTML formatted)                               │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

---

## Prerequisites

### Required Components

1. **Wazuh Server** (v4.x or later)
   - Wazuh Manager with API enabled
   - At least one Wazuh Agent deployed
   - API credentials (username/password)

2. **SOC Copilot** (v1.0.0 or later)
   - Backend services running
   - Redis server for message queues
   - PostgreSQL database

3. **Network Connectivity**
   - SOC Copilot can reach Wazuh API (HTTPS port 55000)
   - Firewall allows outbound connections

### Optional Components

- **Wazuh Indexer** - For log archiving and search
- **Notification Channels**
  - Feishu bot with webhook URL
  - Slack incoming webhook
  - SMTP server for email notifications

---

## Installation

### Step 1: Install Dependencies

```bash
cd /Users/levent/Desktop/sec/backend
pip install pyjwt==2.8.0 aiohttp==3.9.1 backoff==2.2.1
```

### Step 2: Configure Environment Variables

Edit `.env` file:

```bash
# Enable Wazuh Integration
WAZUH_ENABLED=true
WAZUH_REQUIRED=false  # Set to true to fail startup if Wazuh is unavailable

# Wazuh API Configuration
WAZUH_API_URL=https://wazuh.example.com:55000
WAZUH_API_USERNAME=wazuh-wui
WAZUH_API_PASSWORD=your-wazuh-password
WAZUH_API_CERT_PATH=/path/to/wazuh-cert.pem  # Optional, for self-signed certs
WAZUH_VERIFY_SSL=true  # Set to false for self-signed certs

# Log Receiver Configuration
WAZUH_RECEIVER_ENABLED=true
WAZUH_RECEIVER_AUTO_START=true
WAZUH_POLL_INTERVAL=30  # Seconds between polls
WAZUH_BATCH_SIZE=100  # Max alerts per poll
WAZUH_LOOKBACK_MINUTES=5  # Look back on startup
```

### Step 3: Restart Backend Services

```bash
cd /Users/levent/Desktop/sec
docker-compose -f docker-compose.prod.yml restart backend
```

### Step 4: Verify Installation

```bash
# Check logs for Wazuh initialization
docker-compose -f docker-compose.prod.yml logs backend | grep Wazuh

# Expected output:
# Wazuh client initialized: https://wazuh.example.com:55000
# Wazuh log receiver started
```

---

## Configuration

### Basic Configuration

The minimum required configuration:

```bash
WAZUH_ENABLED=true
WAZUH_API_URL=https://wazuh.example.com:55000
WAZUH_API_USERNAME=wazuh-wui
WAZUH_API_PASSWORD=your-password
```

### Advanced Configuration

#### Polling Interval

Adjust how often SOC Copilot fetches new alerts:

```bash
# Poll every 60 seconds instead of 30
WAZUH_POLL_INTERVAL=60
```

**Trade-offs**:

- Lower interval (15-30s): Faster alert delivery, higher API load
- Higher interval (60-120s): Slower alert delivery, lower API load

#### Batch Size

Control max alerts per polling cycle:

```bash
# Fetch up to 200 alerts per poll
WAZUH_BATCH_SIZE=200
```

**Recommendations**:

- Small deployments (<50 agents): 50-100 alerts
- Medium deployments (50-200 agents): 100-200 alerts
- Large deployments (>200 agents): 200-500 alerts

#### Lookback Window

How far back to look on first startup:

```bash
# Look back 1 hour on startup
WAZUH_LOOKBACK_MINUTES=60
```

**Use cases**:

- Fresh installation: 5-15 minutes (avoid alert flood)
- Existing deployment: 60-1440 minutes (catch up on recent alerts)

---

## API Reference

### Health Check

Check Wazuh API connectivity:

```bash
GET /api/v1/wazuh/health
```

**Response**:

```json
{
  "healthy": true,
  "api_url": "https://wazuh.example.com:55000",
  "message": "Connected"
}
```

### Get Agents

List all Wazuh agents:

```bash
GET /api/v1/wazuh/agents?limit=100&status_filter=active
```

**Response**:

```json
[
  {
    "id": "001",
    "name": "prod-server-01",
    "ip": "10.0.0.5",
    "status": "active",
    "os": { "name": "Ubuntu", "version": "22.04" },
    "version": "Wazuh v4.8.0"
  }
]
```

### Get Alerts

Fetch alerts from Wazuh:

```bash
POST /api/v1/wazuh/alerts
Content-Type: application/json

{
  "limit": 100,
  "agent_id": "001",
  "level": 12,
  "start_time": "2026-02-24T00:00:00Z",
  "end_time": "2026-02-24T23:59:59Z"
}
```

### Create Test Alert

Create a test alert to verify integration:

```bash
POST /api/v1/wazuh/test-alert
Content-Type: application/json

{
  "agent_id": "001",
  "rule_id": 5710,
  "severity": "high"
}
```

### Receiver Statistics

Get log receiver statistics:

```bash
GET /api/v1/wazuh/receiver/stats
```

**Response**:

```json
{
  "is_running": true,
  "enabled": true,
  "poll_interval": 30,
  "batch_size": 100,
  "last_poll_time": "2026-02-24T12:00:00Z",
  "total_events_received": 1523,
  "total_alerts_published": 1487,
  "total_errors": 36,
  "success_rate": 97.6
}
```

### Control Receiver

Start/stop/restart the log receiver:

```bash
# Start receiver
POST /api/v1/wazuh/receiver/start

# Stop receiver
POST /api/v1/wazuh/receiver/stop

# Restart receiver
POST /api/v1/wazuh/receiver/restart
```

### Integration Status

Get overall integration status:

```bash
GET /api/v1/wazuh/integration/status
```

**Response**:

```json
{
  "timestamp": "2026-02-24T12:00:00Z",
  "wazuh_api": {
    "configured": true,
    "api_url": "https://wazuh.example.com:55000",
    "authenticated": true
  },
  "log_receiver": {
    "initialized": true,
    "running": true,
    "stats": { ... }
  },
  "message_queue": {
    "available": true
  }
}
```

---

## Testing

### Automated Testing

Run the integration test suite:

```bash
cd /Users/levent/Desktop/sec
python test_wazuh_integration.py
```

**Test Coverage**:

1. Wazuh API connectivity
2. Alert mapper functionality
3. End-to-end integration (Wazuh → Queue → Notification)

### Manual Testing

#### Test 1: Verify API Connectivity

```bash
curl -X GET http://localhost:8000/api/v1/wazuh/health
```

Expected: `{"healthy": true, "api_url": "...", "message": "Connected"}`

#### Test 2: Fetch Agents

```bash
curl -X GET http://localhost:8000/api/v1/wazuh/agents
```

Expected: JSON array of agent objects

#### Test 3: Create Test Alert

```bash
curl -X POST http://localhost:8000/api/v1/wazuh/test-alert \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "001",
    "rule_id": 5710,
    "severity": "high"
  }'
```

Expected: Test alert created and published to queue

#### Test 4: Check Queue

```bash
curl -X GET http://localhost:8000/api/v1/notifications/queue/stats
```

Expected: Shows alerts in queue (pending messages)

#### Test 5: Verify Notification

Check your Feishu/Slack/Email for the test alert notification

---

## Troubleshooting

### Common Issues

#### Issue 1: "Wazuh client not initialized"

**Symptoms**:

- Logs show "Wazuh client not initialized, cannot start receiver"
- API returns 503 Service Unavailable

**Causes**:

- `WAZUH_ENABLED=false` or not set
- Missing required environment variables
- Configuration validation failed

**Solutions**:

1. Check `.env` file has all required variables
2. Verify `WAZUH_ENABLED=true`
3. Check backend logs for specific error
4. Try restarting backend service

#### Issue 2: "Authentication failed: HTTP 401"

**Symptoms**:

- Logs show authentication errors
- Health check returns "Cannot connect to Wazuh API"

**Causes**:

- Incorrect username/password
- Wazuh API not running
- Account locked or disabled

**Solutions**:

1. Verify credentials in Wazuh dashboard
2. Test credentials manually:
   ```bash
   curl -u wazuh-wui:password https://wazuh.example.com:55000/
   ```
3. Check Wazuh API logs:
   ```bash
   tail -f /var/ossec/logs/api.log
   ```

#### Issue 3: "Connection error: SSL verification failed"

**Symptoms**:

- SSL certificate errors in logs
- Cannot connect to Wazuh API

**Causes**:

- Self-signed certificate
- Certificate not trusted
- Certificate expired

**Solutions**:

1. If using self-signed cert, disable verification:
   ```bash
   WAZUH_VERIFY_SSL=false
   ```
2. Or provide certificate path:
   ```bash
   WAZUH_API_CERT_PATH=/path/to/wazuh-cert.pem
   ```
3. Restart backend service

#### Issue 4: "No alerts received"

**Symptoms**:

- Receiver running but no alerts published
- Queue stats show 0 messages

**Causes**:

- No agents generating alerts
- Wazuh rules not configured
- Lookback window too small

**Solutions**:

1. Check Wazuh dashboard for alerts
2. Verify agents are connected and active:
   ```bash
   curl -X GET http://localhost:8000/api/v1/wazuh/agents?status_filter=active
   ```
3. Test with a real security event (e.g., failed SSH login)
4. Increase lookback window and restart receiver

#### Issue 5: "High error rate in receiver stats"

**Symptoms**:

- `success_rate` < 90%
- `total_errors` increasing

**Causes**:

- Network instability
- Wazuh API rate limiting
- Malformed alerts from Wazuh

**Solutions**:

1. Check network connectivity
2. Increase `WAZUH_POLL_INTERVAL` to reduce API load
3. Review error logs for specific issues:
   ```bash
   docker-compose logs backend | grep "Error processing event"
   ```

### Debug Mode

Enable debug logging for Wazuh integration:

```bash
# In .env
LOG_LEVEL=DEBUG
```

Restart backend and check logs:

```bash
docker-compose -f docker-compose.prod.yml logs -f backend | grep -i wazuh
```

---

## Performance Tuning

### Scaling for High-Volume Environments

If you have >200 agents or >1000 alerts/hour:

1. **Increase poll interval** (reduce API load):

   ```bash
   WAZUH_POLL_INTERVAL=60
   ```

2. **Increase batch size** (fetch more per poll):

   ```bash
   WAZUH_BATCH_SIZE=500
   ```

3. **Scale alert workers** (process alerts faster):

   ```bash
   # In docker-compose.prod.yml
   alert-worker:
     deploy:
       replicas: 5  # Increase from 3
   ```

4. **Add Redis persistence** (prevent data loss):
   ```bash
   # In docker-compose.prod.yml
   redis:
     command: redis-server --appendonly yes
   ```

### Monitoring Performance

Key metrics to monitor:

- **Receiver success rate**: Should be >95%
- **Queue depth**: Should not grow continuously
- **Processing latency**: Alert creation to notification <5 minutes

Check metrics:

```bash
# Receiver stats
curl http://localhost:8000/api/v1/wazuh/receiver/stats

# Queue stats
curl http://localhost:8000/api/v1/notifications/queue/stats
```

---

## Next Steps

After completing Wazuh integration:

1. **Configure alert correlation** - Link related alerts
2. **Set up automated playbooks** - Auto-respond to threats
3. **Create custom dashboards** - Visualize Wazuh data
4. **Implement threat hunting** - Proactive threat detection
5. **Fine-tune severity mapping** - Match your organization's needs

---

## Additional Resources

- [Wazuh Documentation](https://documentation.wazuh.com/)
- [MITRE ATT&CK Framework](https://attack.mitre.org/)
- [SOC Copilot Documentation](./README.md)
- [Notification Configuration Guide](./QUICKSTART_NOTIFICATIONS.md)

---

## Support

For issues or questions:

1. Check this guide's troubleshooting section
2. Review logs: `docker-compose logs backend | grep Wazuh`
3. Check Wazuh API logs: `/var/ossec/logs/api.log`
4. Create an issue on GitHub

---

**Document Version**: v1.0.0
**Last Updated**: 2026-02-24
**Maintained By**: SOC Copilot Team
