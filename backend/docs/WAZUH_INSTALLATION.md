# Wazuh Installation and Integration Guide

**Version**: 4.8.0  
**Date**: 2026-02-26  
**Status**: ✅ Ready for Deployment

---

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Installation Steps](#installation-steps)
4. [Configuration](#configuration)
5. [Integration with SOC Copilot](#integration-with-soc-copilot)
6. [Verification](#verification)
7. [Troubleshooting](#troubleshooting)
8. [Maintenance](#maintenance)

---

## Overview

This guide walks you through installing Wazuh (open-source SIEM) and integrating it with SOC Copilot for real-time security alert streaming.

### What is Wazuh?

Wazuh is a unified XDR and SIEM platform that provides:
- **Security Analytics**: Log analysis and threat detection
- **Incident Response**: Automated responses to security events
- **Compliance**: Pre-built regulatory compliance requirements
- **Vulnerability Detection**: Continuous vulnerability assessment
- **File Integrity Monitoring**: Detect file system changes

### Architecture

```
┌─────────────────┐
│  SOC Copilot   │
│  (Frontend)    │
└────────┬────────┘
         │ WebSocket
         ↓
┌─────────────────┐     ┌─────────────────┐
│  SOC Copilot   │────→│  Wazuh Manager  │
│  (Backend)     │     │  (Port 55000)   │
└─────────────────┘     └────────┬────────┘
                                 │
                        ┌────────┴────────┐
                        ↓                 ↓
                ┌──────────────┐  ┌──────────────┐
                │ Wazuh Indexer│  │Wazuh Dashboard│
                │  (OpenSearch)│  │   (Port 5601)  │
                └──────────────┘  └──────────────┘
```

---

## Prerequisites

### System Requirements

**Minimum**:
- CPU: 2 cores
- RAM: 4 GB
- Disk: 20 GB

**Recommended**:
- CPU: 4+ cores
- RAM: 8 GB
- Disk: 50 GB SSD

### Software Requirements

- **Docker**: 20.10+ (check with `docker --version`)
- **Docker Compose**: 2.0+ (check with `docker compose version`)
- **Ports Available**:
  - `5601` - Wazuh Dashboard
  - `55000` - Wazuh API
  - `9200` - OpenSearch
  - `1514-1516` - Wazuh Agent connections
  - `5432` - PostgreSQL (optional)

### Verification

```bash
# Check Docker
docker --version

# Check Docker Compose
docker compose version

# Check if ports are available
netstat -tuln | grep -E '5601|55000|9200|1514|5432'
```

---

## Installation Steps

### Step 1: Prepare Environment

```bash
# Navigate to project directory
cd /Users/levent/Desktop/sec

# Copy environment template
cp .env.wazuh.example .env.wazuh

# Edit .env.wazuh and update passwords
nano .env.wazuh  # or use your preferred editor
```

### Step 2: Run Installation Script

```bash
# Make script executable (if needed)
chmod +x setup_wazuh.sh

# Run installation
./setup_wazuh.sh
```

The script will:
1. ✓ Verify Docker and Docker Compose are installed
2. ✓ Create configuration directories
3. ✓ Generate Wazuh configuration files
4. ✓ Start Wazuh stack using Docker Compose
5. ✓ Wait for all services to be healthy
6. ✓ Display access credentials

### Step 3: Verify Installation

```bash
# Check service status
docker compose -f docker-compose.wazuh.yml ps

# Check service health
curl -k https://localhost:55000/healthcheck
```

**Expected Output**:
```
NAME                IMAGE                              STATUS
wazuh.dashboard     wazuh/wazuh-dashboard:4.8.0       Up (healthy)
wazuh.indexer       wazuh/wazuh-indexer:4.8.0         Up (healthy)
wazuh.manager       wazuh/wazuh-manager:4.8.0         Up (healthy)
wazuh.db            postgres:15-alpine                Up (healthy)
```

---

## Configuration

### Accessing Wazuh Dashboard

1. Open browser: `https://localhost:5601`
2. Accept SSL warning (self-signed certificate)
3. Login with:
   - Username: `admin`
   - Password: `ChangeThisPassword123!`

### Change Default Passwords

**⚠️ CRITICAL**: Change default passwords immediately!

```bash
# Update .env.wazuh
nano .env.wazuh

# Restart services
docker compose -f docker-compose.wazuh.yml restart
```

### Configure Wazuh Manager

Edit `config/wazuh-manager/ossec.conf`:

```xml
<ossec_config>
  <global>
    <email_notification>yes</email_notification>
    <email_to>security@example.com</email_to>
    <email_from>wazuh@example.com</email_from>
    <smtp_server>smtp.example.com</smtp_server>
  </global>
  
  <!-- Add custom rules and decoders here -->
</ossec_config>
```

Restart after changes:
```bash
docker compose -f docker-compose.wazuh.yml restart wazuh.manager
```

---

## Integration with SOC Copilot

### Step 1: Run Integration Script

```bash
./integrate_wazuh.sh
```

This script will:
1. ✓ Verify Wazuh is running
2. ✓ Configure backend `.env` with Wazuh settings
3. ✓ Test Wazuh API connection
4. ✓ Optionally install Wazuh agent
5. ✓ Restart backend service

### Step 2: Verify Backend Configuration

Check `backend/.env`:

```bash
# Should contain:
WAZUH_ENABLED=true
WAZUH_API_URL=https://localhost:55000
WAZUH_API_USERNAME=wazuh-wui
WAZUH_API_PASSWORD=wazuh-wui-password
WAZUH_VERIFY_SSL=false
WAZUH_RECEIVER_ENABLED=true
WAZUH_RECEIVER_AUTO_START=true
```

### Step 3: Restart Backend

```bash
cd backend
pkill -f "python.*main.py"
python main.py &
```

Or use the integration script which offers to do this automatically.

---

## Verification

### Test Wazuh API Connection

```bash
# Test Wazuh API
curl -k -u wazuh-wui:wazuh-wui-password \
  https://localhost:55000/?pretty=true

# Expected: JSON response with API information
```

### Test SOC Copilot Integration

```bash
# Use the test script
./test_wazuh_stream.sh
```

### Verify Frontend Connection

1. Open SOC Copilot in browser
2. Navigate to `/zh/wazuh` or `/en/wazuh`
3. Should see "✅ Connected to Wazuh real-time stream"

### Send Test Alert

```bash
# Login to SOC Copilot and get JWT token
TOKEN="your_jwt_token"

# Start stream service
curl -X POST http://localhost:8000/api/v1/wazuh/stream/start \
  -H "Authorization: Bearer $TOKEN"

# Send test alert
curl -X POST http://localhost:8000/api/v1/wazuh/stream/test-alert \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "agent_id": "001",
    "severity": "high",
    "event_type": "ssh_bruteforce",
    "count": 3
  }'
```

Expected: Frontend should display test alerts in real-time.

---

## Troubleshooting

### Problem 1: Services Not Starting

**Symptoms**: Containers exit immediately or fail health checks

**Solutions**:

```bash
# Check logs
docker compose -f docker-compose.wazuh.yml logs -f

# Common issue: Port conflicts
# Check if ports are already in use
lsof -i :5601
lsof -i :55000
lsof -i :9200

# Solution: Stop conflicting services or change ports
```

### Problem 2: Cannot Connect to Wazuh API

**Symptoms**: Connection refused or timeout

**Solutions**:

```bash
# Check if service is running
docker compose -f docker-compose.wazuh.yml ps wazuh.manager

# Check service health
curl -k https://localhost:55000/healthcheck

# Check credentials in .env.wazuh
cat .env.wazuh | grep WAZUH_API
```

### Problem 3: Frontend Shows "Disconnected"

**Symptoms**: `/wazuh` page shows "Not connected to Wazuh real-time stream"

**Solutions**:

1. **Check backend logs**:
```bash
tail -f backend/server.err | grep -i wazuh
```

2. **Verify Wazuh is enabled**:
```bash
grep WAZUH_ENABLED backend/.env
# Should be: WAZUH_ENABLED=true
```

3. **Start stream service**:
```bash
TOKEN="your_jwt_token"
curl -X POST http://localhost:8000/api/v1/wazuh/stream/start \
  -H "Authorization: Bearer $TOKEN"
```

4. **Check service status**:
```bash
curl http://localhost:8000/api/v1/wazuh/stream/status \
  -H "Authorization: Bearer $TOKEN"
```

### Problem 4: No Alerts Receiving

**Symptoms**: Connection successful but no alerts displayed

**Solutions**:

```bash
# Send test alert
curl -X POST http://localhost:8000/api/v1/wazuh/stream/test-alert \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"agent_id": "001", "severity": "high", "count": 5}'

# Check Wazuh Dashboard for actual alerts
# https://localhost:5601

# Install Wazuh agent to generate real alerts
./integrate_wazuh.sh
# Select 'y' when asked about agent installation
```

### Problem 5: SSL Certificate Errors

**Symptoms**: `SSL: CERTIFICATE_VERIFY_FAILED`

**Solutions**:

```bash
# For development, disable SSL verification
# In backend/.env:
WAZUH_VERIFY_SSL=false

# Or add certificate to trust store (for production)
# Copy certificate from:
# docker compose -f docker-compose.wazuh.yml exec wazuh.manager \
#   cat /var/ossec/api/configuration/ssl/server.crt
```

---

## Maintenance

### Viewing Logs

```bash
# All services
docker compose -f docker-compose.wazuh.yml logs -f

# Specific service
docker compose -f docker-compose.wazuh.yml logs -f wazuh.manager
docker compose -f docker-compose.wazuh.yml logs -f wazuh.indexer
docker compose -f docker-compose.wazuh.yml logs -f wazuh.dashboard
```

### Backing Up Data

```bash
# Backup Wazuh manager data
docker run --rm \
  -v wazuh-manager-data:/data \
  -v $(pwd)/backups:/backup \
  alpine tar czf /backup/wazuh-manager-$(date +%Y%m%d).tar.gz -C /data .

# Backup Indexer data
docker run --rm \
  -v wazuh-indexer-data:/data \
  -v $(pwd)/backups:/backup \
  alpine tar czf /backup/wazuh-indexer-$(date +%Y%m%d).tar.gz -C /data .
```

### Restoring Data

```bash
# Restore Wazuh manager data
docker run --rm \
  -v wazuh-manager-data:/data \
  -v $(pwd)/backups:/backup \
  alpine tar xzf /backup/wazuh-manager-20260226.tar.gz -C /data

# Restart services
docker compose -f docker-compose.wazuh.yml restart
```

### Updating Wazuh

```bash
# Pull new images
docker compose -f docker-compose.wazuh.yml pull

# Recreate containers with new images
docker compose -f docker-compose.wazuh.yml up -d --force-recreate

# Verify update
docker compose -f docker-compose.wazuh.yml ps
```

### Stopping Services

```bash
# Stop all services
docker compose -f docker-compose.wazuh.yml down

# Stop and remove volumes (⚠️ deletes data!)
docker compose -f docker-compose.wazuh.yml down -v
```

### Monitoring Resources

```bash
# Check container resource usage
docker stats

# Check disk usage
docker system df

# Clean up unused resources
docker system prune -a
```

---

## Performance Tuning

### Increase Memory for OpenSearch

Edit `docker-compose.wazuh.yml`:

```yaml
wazuh.indexer:
  environment:
    - OPENSEARCH_JAVA_OPTS=-Xms2g -Xmx2g  # Increase from 512m
```

### Adjust Indexer Retention

In Wazuh Dashboard → Stack Management → Index Patterns:
- Set retention period (e.g., 30 days)
- Configure index lifecycle management

### Optimize Log Parsing

Edit `config/wazuh-manager/ossec.conf`:
```xml
<ossec_config>
  <ruleset>
    <!-- Only load needed rules -->
    <rule_dir>ruleset/ssh</rule_dir>
    <rule_dir>ruleset/web</rule_dir>
  </ruleset>
</ossec_config>
```

---

## Security Best Practices

1. **Change Default Passwords**
   - Update `.env.wazuh` with strong passwords
   - Update Wazuh Dashboard admin password

2. **Enable SSL/TLS**
   - Use valid SSL certificates in production
   - Enable `WAZUH_VERIFY_SSL=true` after certificates are in place

3. **Network Isolation**
   - Use dedicated Docker network
   - Expose only necessary ports
   - Use firewall rules to restrict access

4. **Regular Updates**
   - Keep Wazuh images updated
   - Monitor security advisories
   - Test updates in staging first

5. **Access Control**
   - Use RBAC in Wazuh Dashboard
   - Limit API access with firewall rules
   - Rotate credentials regularly

---

## Additional Resources

- **Wazuh Documentation**: https://documentation.wazuh.com
- **Wazuh Community**: https://wazuh.com/community
- **SOC Copilot Docs**: `docs/README.md`
- **Troubleshooting**: `WAZUH_STREAM_TROUBLESHOOT.md`

---

## Support

For issues or questions:
1. Check logs: `docker compose -f docker-compose.wazuh.yml logs -f`
2. Review troubleshooting section above
3. Check Wazuh documentation
4. Open issue in project repository

---

**Installation Guide Version**: v1.0.0  
**Last Updated**: 2026-02-26  
**Wazuh Version**: 4.8.0
