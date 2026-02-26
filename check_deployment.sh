#!/bin/bash
# Wazuh Security Stack Health Check

echo "🔍 SOC Copilot Security Stack - Health Check"
echo "=========================================="
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check function
check_service() {
    local name=$1
    local url=$2
    local auth=$3

    echo -n "Testing $name... "

    if [ -n "$auth" ]; then
        response=$(curl -s -u "$auth" "$url" -o /dev/null -w "%{http_code}" --max-time 5)
    else
        response=$(curl -s "$url" -o /dev/null -w "%{http_code}" --max-time 5)
    fi

    if [ "$response" = "200" ] || [ "$response" = "401" ]; then
        echo -e "${GREEN}✅ OK${NC}"
        return 0
    else
        echo -e "${RED}❌ FAILED (HTTP $response)${NC}"
        return 1
    fi
}

# Check Docker containers
echo "📦 Docker Containers:"
echo "--------------------"
docker-compose -f /Users/levent/Desktop/sec/docker-compose.security.yml ps 2>/dev/null || echo -e "${YELLOW}No containers running yet${NC}"
echo ""

# Check services
echo "🌐 Service Endpoints:"
echo "--------------------"
check_service "Elasticsearch" "http://localhost:9200/_cluster/health" "elastic:SecureP@ssw0rd123!"
check_service "Kibana" "http://localhost:5601/api/status" ""
echo ""

# Check Wazuh (may need SSL skip)
echo -n "Testing Wazuh Manager... "
if curl -s -k -u "wazuh-wui:WazuhP@ssw0rd123!" "https://localhost:55000/" -o /dev/null --max-time 5; then
    echo -e "${GREEN}✅ OK${NC}"
else
    echo -e "${YELLOW}⚠️  Starting up...${NC}"
fi

echo -n "Testing Wazuh Dashboard... "
if curl -s "https://localhost:444" -o /dev/null --max-time 5; then
    echo -e "${GREEN}✅ OK${NC}"
else
    echo -e "${YELLOW}⚠️  Starting up...${NC}"
fi
echo ""

# Check SOC Copilot Backend
echo "🔧 SOC Copilot Backend:"
echo "----------------------"
check_service "Backend API" "http://localhost:8000/health" ""
echo ""

# Summary
echo "📊 Summary:"
echo "----------"
echo "Kibana:      http://localhost:5601"
echo "Wazuh:       https://localhost:444"
echo "Elasticsearch: http://localhost:9200"
echo "SOC Backend: http://localhost:8000"
echo ""

echo "💡 Next steps:"
echo "  1. Wait for all services to be healthy"
echo "  2. Access Kibana: http://localhost:5601"
echo "  3. Access Wazuh: https://localhost:444"
echo "  4. Send test alerts to verify integration"
echo ""
