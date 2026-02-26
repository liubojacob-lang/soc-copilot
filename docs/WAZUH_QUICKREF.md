# Wazuh Integration Quick Reference

**Version**: v1.0.0

---

## Setup (2 minutes)

```bash
# Run the setup script
./setup_wazuh.sh

# Or manually edit .env
WAZUH_ENABLED=true
WAZUH_API_URL=https://wazuh.example.com:55000
WAZUH_API_USERNAME=wazuh-wui
WAZUH_API_PASSWORD=your-password

# Restart backend
docker-compose restart backend
```

---

## API Endpoints

### Health & Status

```bash
# Check connection
GET /api/v1/wazuh/health

# Integration status
GET /api/v1/wazuh/integration/status

# Receiver stats
GET /api/v1/wazuh/receiver/stats
```

### Data Retrieval

```bash
# List agents
GET /api/v1/wazuh/agents?limit=100&status_filter=active

# Get agent info
GET /api/v1/wazuh/agents/{agent_id}

# Fetch alerts
POST /api/v1/wazuh/alerts
{
  "limit": 100,
  "agent_id": "001",
  "level": 12
}

# Alerts summary
GET /api/v1/wazuh/alerts/summary
```

### Control

```bash
# Start receiver
POST /api/v1/wazuh/receiver/start

# Stop receiver
POST /api/v1/wazuh/receiver/stop

# Restart receiver
POST /api/v1/wazuh/receiver/restart

# Configure receiver
POST /api/v1/wazuh/receiver/configure
{
  "enabled": true,
  "poll_interval": 30,
  "batch_size": 100
}
```

### Testing

```bash
# Create test alert
POST /api/v1/wazuh/test-alert
{
  "agent_id": "001",
  "rule_id": 5710,
  "severity": "high"
}
```

---

## Severity Mapping

| Wazuh Level | SOC Severity | Color | Response Time |
|------------|--------------|-------|---------------|
| 0-3 | Low | Blue | 24h |
| 4-7 | Medium | Yellow | 8h |
| 8-12 | High | Orange | 1h |
| 13-15 | Critical | Red | Immediate |

---

## File Locations

```
backend/services/
├── wazuh_client.py           # Wazuh API client
├── wazuh_alert_mapper.py     # Alert schema mapper
└── wazuh_log_receiver.py     # Log polling service

backend/routers/
└── wazuh_integration.py      # API endpoints

docs/
└── wazuh_integration.md      # Full documentation

setup_wazuh.sh                # Setup script
test_wazuh_integration.py     # Test suite
```

---

## Common Commands

```bash
# Test integration
python test_wazuh_integration.py

# Check logs
docker-compose logs backend | grep Wazuh

# Restart receiver
curl -X POST http://localhost:8000/api/v1/wazuh/receiver/restart

# Check queue stats
curl http://localhost:8000/api/v1/notifications/queue/stats

# View agents
curl http://localhost:8000/api/v1/wazuh/agents
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "Not initialized" | Check `WAZUH_ENABLED=true` in .env |
| "Auth failed" | Verify username/password in Wazuh |
| "SSL error" | Set `WAZUH_VERIFY_SSL=false` for self-signed certs |
| "No alerts" | Check agents are active in Wazuh dashboard |
| High error rate | Increase `WAZUH_POLL_INTERVAL` to 60 |

---

## Configuration Options

```bash
# Required
WAZUH_ENABLED=true
WAZUH_API_URL=https://wazuh.example.com:55000
WAZUH_API_USERNAME=wazuh-wui
WAZUH_API_PASSWORD=password

# Optional (performance tuning)
WAZUH_POLL_INTERVAL=30         # Seconds
WAZUH_BATCH_SIZE=100           # Alerts per poll
WAZUH_LOOKBACK_MINUTES=5       # Startup lookback
WAZUH_VERIFY_SSL=true          # SSL verification
WAZUH_RECEIVER_AUTO_START=true # Auto-start
```

---

## Monitoring

**Key Metrics**:
- Receiver success rate: Should be >95%
- Queue depth: Should not grow continuously
- Poll latency: Should be <5 seconds

**Check**:
```bash
curl http://localhost:8000/api/v1/wazuh/receiver/stats
```

---

## Support

- Full docs: `docs/wazuh_integration.md`
- Setup: `./setup_wazuh.sh`
- Test: `python test_wazuh_integration.py`
- Logs: `docker-compose logs backend | grep Wazuh`
