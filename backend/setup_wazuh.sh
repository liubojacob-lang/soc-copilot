#!/bin/bash
# Wazuh Installation and Setup Script
# This script sets up Wazuh using Docker Compose

set -e  # Exit on error

echo "================================"
echo "Wazuh Installation Script"
echo "================================"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Error: Docker is not installed${NC}"
    echo "Please install Docker first: https://docs.docker.com/get-docker/"
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo -e "${RED}Error: Docker Compose is not installed${NC}"
    echo "Please install Docker Compose first: https://docs.docker.com/compose/install/"
    exit 1
fi

echo -e "${GREEN}✓ Docker and Docker Compose are installed${NC}"
echo ""

# Check if .env.wazuh exists
if [ ! -f .env.wazuh ]; then
    echo -e "${YELLOW}Creating .env.wazuh from template...${NC}"
    cp .env.wazuh.example .env.wazuh
    echo -e "${YELLOW}⚠️  Please edit .env.wazuh and update the passwords!${NC}"
    echo ""
    read -p "Press Enter to continue after updating .env.wazuh..."
fi

# Create necessary directories
echo -e "${YELLOW}Creating configuration directories...${NC}"
mkdir -p config/wazuh-indexer
mkdir -p config/wazuh-manager/rules
mkdir -p config/wazuh-manager/decoders
mkdir -p config/wazuh-dashboard
echo -e "${GREEN}✓ Directories created${NC}"
echo ""

# Generate OpenSearch configuration
echo -e "${YELLOW}Generating OpenSearch configuration...${NC}"
cat > config/wazuh-indexer/opensearch.yml <<EOF
cluster.name: wazuh-cluster
network.host: 0.0.0.0
discovery.type: single-node
plugins.security.ssl.http.enabled: true
plugins.security.ssl.transport.enabled: true
plugins.security.ssl.http.pemcert_filepath: certs/node.pem
plugins.security.ssl.http.pemkey_filepath: certs/node-key.pem
plugins.security.ssl.transport.pemcert_filepath: certs/node.pem
plugins.security.ssl.transport.pemkey_filepath: certs/node-key.pem
plugins.security.ssl.transport.pemtrustedcas_filepath: certs/ca.pem
plugins.security.allow_default_init_securityindex: true
plugins.security.authcz.admin_dn:
  - CN=admin,O=Wazuh,L=California,C=US
plugins.security.check_snapshot_restore_write_privileges: true
plugins.security.enable_snapshot_restore_privilege: true
EOF

# Generate Wazuh API configuration
cat > config/wazuh-manager/api.yaml <<EOF
host: 0.0.0.0
port: 55000
basic_auth:
  username: wazuh-wui
  password: wazuh-wui-password
HTTPS: yes
key: /var/ossec/api/configuration/ssl/server.key
cert: /var/ossec/api/configuration/ssl/server.crt
ssl: yes
logs:
  level: info
  format: plain
access:
  - IP: 0.0.0.0/0
  - IP: ::/0
use_only_authd: false
drop_privileges: true
connection_timeout: 10
max_upload_size: 10M
EOF

# Generate Wazuh Dashboard configuration
cat > config/wazuh-dashboard/opensearch_dashboards.yml <<EOF
server.host: 0.0.0.0
server.port: 5601
opensearch.ssl.verificationMode: none
opensearch.requestHeadersWhitelist: ["authorization"]
opensearch_security.multitenancy.enabled: false
opensearch_security.readonly_mode.roles: ["kibana_read_only"]
opensearch_security.cookie.secure: false
opensearch_security.cookie.password: wazuh-dashboard-cookie-password
server.ssl.enabled: true
server.ssl.certificate: /usr/share/wazuh-dashboard/config/certs/wazuh-dashboard.pem
server.ssl.key: /usr/share/wazuh-dashboard/config/certs/wazuh-dashboard-key.pem
EOF

cat > config/wazuh-dashboard/wazuh.yml <<EOF
hosts:
  - url: https://wazuh.manager:55000
    username: wazuh-wui
    password: wazuh-wui-password
api:
  url: https://wazuh.manager:55000
  username: wazuh-wui
  password: wazuh-wui-password
EOF

echo -e "${GREEN}✓ Configuration files generated${NC}"
echo ""

# Generate basic ossec.conf
echo -e "${YELLOW}Generating Wazuh manager configuration...${NC}"
cat > config/wazuh-manager/ossec.conf <<EOF
<ossec_config>
  <global>
    <email_notification>no</email_notification>
    <json_out_format>yes</json_out_format>
  </global>

  <alerts>
    <log>all</log>
  </alerts>

  <ruleset>
    <rule_dir>rules</rule_dir>
    <rule_dir>ruleset/attackers</rule_dir>
    <rule_dir>ruleset/attacks</rule_dir>
    <rule_dir>ruleset/brute-force</rule_dir>
    <rule_dir>ruleset/compat</rule_dir>
    <rule_dir>ruleset/images</rule_dir>
    <rule_dir>ruleset/malware</rule_dir>
    <rule_dir>ruleset/pua</rule_dir>
    <rule_dir>ruleset/schemas</rule_dir>
    <rule_dir>ruleset/syslog</rule_dir>
    <rule_dir>ruleset/virus</rule_dir>
    <rule_dir>ruleset/zeek</rule_dir>
    <rule_dir>ruleset/wazuh</rule_dir>
  </ruleset>

  <remote>
    <connection>secure</connection>
    <port>1514</port>
    <protocol>tcp</protocol>
    <queue_size>131072</queue_size>
  </remote>
</ossec_config>
EOF

echo -e "${GREEN}✓ Wazuh manager configuration generated${NC}"
echo ""

# Start Wazuh stack
echo -e "${YELLOW}Starting Wazuh stack...${NC}"
docker compose -f docker-compose.wazuh.yml up -d

echo ""
echo -e "${GREEN}✓ Wazuh stack is starting...${NC}"
echo ""
echo "Waiting for services to be healthy (this may take a few minutes)..."
echo ""

# Wait for Wazuh Indexer
echo -n "Waiting for Wazuh Indexer..."
until docker compose -f docker-compose.wazuh.yml exec -T wazuh.indexer curl -k -u admin:ChangeThisPassword123! https://localhost:9200/_cluster/health &> /dev/null; do
    echo -n "."
    sleep 5
done
echo -e " ${GREEN}✓${NC}"

# Wait for Wazuh Manager
echo -n "Waiting for Wazuh Manager..."
until docker compose -f docker-compose.wazuh.yml exec -T wazuh.manager curl -k https://localhost:55000/healthcheck &> /dev/null; do
    echo -n "."
    sleep 5
done
echo -e " ${GREEN}✓${NC}"

# Wait for Wazuh Dashboard
echo -n "Waiting for Wazuh Dashboard..."
until docker compose -f docker-compose.wazuh.yml exec -T wazuh.dashboard curl -k https://localhost:5601/api/status &> /dev/null; do
    echo -n "."
    sleep 5
done
echo -e " ${GREEN}✓${NC}"

echo ""
echo -e "${GREEN}================================${NC}"
echo -e "${GREEN}Wazuh installation complete!${NC}"
echo -e "${GREEN}================================${NC}"
echo ""
echo "Access Wazuh services:"
echo "  - Wazuh Dashboard: https://localhost:5601"
echo "    Username: admin"
echo "    Password: ChangeThisPassword123!"
echo ""
echo "  - Wazuh API: https://localhost:55000"
echo "    Username: wazuh-wui"
echo "    Password: wazuh-wui-password"
echo ""
echo "  - OpenSearch: https://localhost:9200"
echo "    Username: admin"
echo "    Password: ChangeThisPassword123!"
echo ""
echo -e "${YELLOW}⚠️  IMPORTANT: Change default passwords!${NC}"
echo ""
echo "Next steps:"
echo "  1. Login to Wazuh Dashboard at https://localhost:5601"
echo "  2. Configure SOC Copilot to connect to Wazuh"
echo "  3. Run: ./integrate_wazuh.sh"
echo ""
echo "Useful commands:"
echo "  - View logs: docker compose -f docker-compose.wazuh.yml logs -f"
echo "  - Stop stack: docker compose -f docker-compose.wazuh.yml down"
echo "  - Restart: docker compose -f docker-compose.wazuh.yml restart"
echo ""
