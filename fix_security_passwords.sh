#!/bin/bash
# Security Fix Script - Remove hardcoded passwords
# Run with: bash fix_security_passwords.sh

set -e

echo "🔧 Fixing hardcoded passwords in docker-compose files..."

# Fix docker-compose.security.yml
echo "📝 Fixing docker-compose.security.yml..."
sed -i '' 's/INDEXER_PASSWORD=${ELASTICSEARCH_PASSWORD:-SecureP@ssw0rd123!}/INDEXER_PASSWORD=${ELASTICSEARCH_PASSWORD:?ERROR: ELASTICSEARCH_PASSWORD is required}/g' docker-compose.security.yml
sed -i '' 's/API_PASSWORD=${WAZUH_API_PASSWORD:-WazuhP@ssw0rd123!}/API_PASSWORD=${WAZUH_API_PASSWORD:?ERROR: WAZUH_API_PASSWORD is required}/g' docker-compose.security.yml

# Fix .env.security - replace real passwords with placeholders
echo "📝 Fixing .env.security..."
sed -i '' 's/ELASTICSEARCH_PASSWORD=SecureP@ssw0rd123!/ELASTICSEARCH_PASSWORD=CHANGE_ME_USE_OPENSSL_RAND_BASE64_32/g' .env.security
sed -i '' 's/WAZUH_API_PASSWORD=WazuhP@ssw0rd123!/WAZUH_API_PASSWORD=CHANGE_ME_USE_OPENSSL_RAND_BASE64_32/g' .env.security
sed -i '' 's/WAZUH_DASHBOARD_PASSWORD=WazuhP@ssw0rd123!/WAZUH_DASHBOARD_PASSWORD=CHANGE_ME_USE_OPENSSL_RAND_BASE64_32/g' .env.security

# Fix .env.wazuh.example
echo "📝 Fixing .env.wazuh.example..."
sed -i '' 's/WAZUH_INDEXER_PASSWORD=ChangeThisPassword123!/WAZUH_INDEXER_PASSWORD=<CHANGE_ME_USE_OPENSSL_RAND_BASE64_32>/g' .env.wazuh.example
sed -i '' 's/FILEBEAT_PASSWORD=FilebeatPassword123!/FILEBEAT_PASSWORD=<CHANGE_ME_USE_OPENSSL_RAND_BASE64_32>/g' .env.wazuh.example
sed -i '' 's/WAZUH_API_PASSWORD=wazuh-wui-password/WAZUH_API_PASSWORD=<CHANGE_ME_USE_OPENSSL_RAND_BASE64_32>/g' .env.wazuh.example
sed -i '' 's/WAZUH_DB_PASSWORD=wazuh-db-password/WAZUH_DB_PASSWORD=<CHANGE_ME_USE_OPENSSL_RAND_BASE64_32>/g' .env.wazuh.example

echo "✅ All hardcoded passwords have been replaced with placeholders!"
echo ""
echo "📋 Next steps:"
echo "1. Generate secure passwords: openssl rand -base64 32"
echo "2. Update your .env files with the generated passwords"
echo "3. Add .env.security to .gitignore if not already present"
