#!/bin/bash
# Generate self-signed SSL certificates for development
# For production, use Let's Encrypt or a trusted CA

SSL_DIR="./nginx/ssl"
CERT_FILE="$SSL_DIR/fullchain.pem"
KEY_FILE="$SSL_DIR/privkey.pem"

# Create SSL directory
mkdir -p "$SSL_DIR"

# Check if certificates already exist
if [ -f "$CERT_FILE" ] && [ -f "$KEY_FILE" ]; then
    echo "⚠️  SSL certificates already exist"
    echo "   To regenerate, delete the existing certificates first:"
    echo "   rm $CERT_FILE $KEY_FILE"
    exit 0
fi

echo "🔐 Generating self-signed SSL certificates..."

# Generate self-signed certificate
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout "$KEY_FILE" \
    -out "$CERT_FILE" \
    -subj "/C=US/ST=State/L=City/O=SOC Copilot/CN=localhost" \
    -addext "subjectAltName=DNS:localhost,IP:127.0.0.1"

# Set proper permissions
chmod 644 "$CERT_FILE"
chmod 600 "$KEY_FILE"

echo "✅ SSL certificates generated successfully!"
echo "   Certificate: $CERT_FILE"
echo "   Private Key: $KEY_FILE"
echo ""
echo "⚠️  NOTE: These are self-signed certificates for DEVELOPMENT only"
echo "   For production, use Let's Encrypt:"
echo "   certbot certonly --nginx -d your-domain.com"
