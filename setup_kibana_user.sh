#!/bin/bash
# Setup kibana_system user password in Elasticsearch

echo "🔧 Setting up kibana_system user..."

# Wait for Elasticsearch to be ready
until curl -s http://localhost:9200/_cluster/health > /dev/null; do
    echo "Waiting for Elasticsearch..."
    sleep 5
done

echo "Elasticsearch is ready. Setting kibana_system password..."

# Set kibana_system password
curl -X POST -u elastic:SecureP@ssw0rd123! \
  "http://localhost:9200/_security/user/kibana_system/_password" \
  -H "Content-Type: application/json" \
  -d '{"password": "KibanaP@ssw0rd123!"}' \
  -s | python3 -m json.tool

echo ""
echo "✅ kibana_system password set to: KibanaP@ssw0rd123!"
echo ""
echo "Now restart Kibana:"
echo "  docker-compose -f docker-compose.security.yml restart kibana"
