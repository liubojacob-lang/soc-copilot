#!/usr/bin/env python3
"""Export FastAPI OpenAPI schema to openapi.json."""

import json
import os
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = ROOT_DIR / "backend"
sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault("ENVIRONMENT", "development")
os.environ.setdefault("AUTO_RUN_MIGRATIONS", "false")

try:
    from main import app
except ImportError as e:
    print(f"Error importing FastAPI app: {e}", file=sys.stderr)
    sys.exit(1)

output_path = ROOT_DIR / "openapi.json"
print(f"Generating OpenAPI schema from FastAPI ({app.title} v{app.version})...")
schema = app.openapi()

with open(output_path, "w", encoding="utf-8") as f:
    json.dump(schema, f, indent=2, ensure_ascii=False)

print(f"✅ Successfully exported OpenAPI schema to {output_path} ({len(app.routes)} routes)")
