#!/bin/bash
# Fix .env.security permissions and update passwords
# Run with: sudo bash fix_env_security.sh

ENV_FILE="/Users/levent/Desktop/Projects/sec/.env.security"

echo "🔧 Fixing .env.security..."

# Fix permissions
sudo chown $(whoami):staff "$ENV_FILE"
sudo chmod 644 "$ENV_FILE"

# Replace hardcoded passwords
sed -i '' 's/ELASTICSEARCH_PASSWORD=SecureP@ssw0rd123!/ELASTICSEARCH_PASSWORD=CHANGE_ME_USE_OPENSSL_RAND_BASE64_32/g' "$ENV_FILE"
sed -i '' 's/WAZUH_API_PASSWORD=WazuhP@ssw0rd123!/WAZUH_API_PASSWORD=CHANGE_ME_USE_OPENSSL_RAND_BASE64_32/g' "$ENV_FILE"
sed -i '' 's/WAZUH_DASHBOARD_PASSWORD=WazuhP@ssw0rd123!/WAZUH_DASHBOARD_PASSWORD=CHANGE_ME_USE_OPENSSL_RAND_BASE64_32/g' "$ENV_FILE"

echo "✅ .env.security updated!"
echo "📋 Next: Generate strong passwords with: openssl rand -base64 32"
