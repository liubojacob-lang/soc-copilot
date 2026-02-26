#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "$0")/.." && pwd)
SRC_DIR="$ROOT_DIR/ai-assistant-release"
DEST_DIR="$ROOT_DIR/ai-assistant-release-sanitized"
ZIP_OUT="$ROOT_DIR/ai-assistant-release-sanitized.zip"

echo "[sanitize] Preparing sanitized release at $DEST_DIR"
rm -rf "$DEST_DIR"
mkdir -p "$DEST_DIR"

# Copy all files to destination
rsync -av "$SRC_DIR/" "$DEST_DIR/"

# If .env exists, replace secrets with placeholders
ENV_FILE="$DEST_DIR/.env"
if [ -f "$ENV_FILE" ]; then
  echo "[sanitize] Sanitizing $ENV_FILE"
  declare -a KEYS=(
    NVIDIA_API_KEY ZHIPU_API_KEY MOONSHOT_API_KEY OPENROUTER_API_KEY ANTHROPIC_API_KEY OPENAI_API_KEY JWT_SECRET SECRET_ENCRYPTION_KEY OTX_API_KEY
  )
  declare -a PLACEHOLDERS=(
    REPLACE_WITH_YOUR_NVIDIA_API_KEY REPLACE_WITH_YOUR_ZHIPU_API_KEY REPLACE_WITH_YOUR_MOONSHOT_API_KEY REPLACE_WITH_YOUR_OPENROUTER_API_KEY REPLACE_WITH_YOUR_ANTHROPIC_API_KEY REPLACE_WITH_YOUR_OPENAI_API_KEY REPLACE_WITH_YOUR_JWT_SECRET REPLACE_WITH_YOUR_SECRET_ENC_KEY REPLACE_WITH_YOUR_OTX_API_KEY
  )

  # simple mapping helper
  for i in ${!KEYS[@]}; do
    key="${KEYS[$i]}"
    placeholder="${PLACEHOLDERS[$i]}"
    # Use a safe sed replacement; support macOS (BSD sed) and GNU sed by fallback
    if command -v sed >/dev/null 2>&1; then
      if sed --version >/dev/null 2>&1; then
        sed -i "s|^${key}=.*|${key}=${placeholder}|" "$ENV_FILE" 2>/dev/null || sed -i '' "s|^${key}=.*|${key}=${placeholder}|" "$ENV_FILE" || true
      else
        sed -i '' -e "s|^${key}=.*|${key}=${placeholder}|" "$ENV_FILE" || true
      fi
    fi
  done
fi

# Also sanitize any top-level .env in demo app if present
DEMO_ENV="$DEST_DIR/ai-assistant-demo-app/.env"
if [ -f "$DEMO_ENV" ]; then
  echo "[sanitize] Sanitizing project demo env"
  sed -i '' -E 's/^[A-Z_]+=.*/REPLACED/' "$DEMO_ENV" 2>/dev/null || true
fi

# Create a ZIP package for easy distribution
echo "[sanitize] Creating ZIP package: $ZIP_OUT"
cd "$ROOT_DIR"
zip -r "$ZIP_OUT" ai-assistant-release >/dev/null 2>&1
echo "[sanitize] Done. Package: $ZIP_OUT"
