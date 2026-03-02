#!/usr/bin/env python3
"""Test script to verify imports work correctly."""

import sys
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

print(f"Python path: {sys.path}")
print(f"Backend directory: {backend_dir}")

try:
    from core.config import settings
    print("✓ Successfully imported core.config")
except Exception as e:
    print(f"✗ Failed to import core.config: {e}")

try:
    from core.logger import get_logger
    print("✓ Successfully imported core.logger")
except Exception as e:
    print(f"✗ Failed to import core.logger: {e}")

try:
    from db.session import AsyncSessionLocal
    print("✓ Successfully imported db.session")
except Exception as e:
    print(f"✗ Failed to import db.session: {e}")

try:
    from routers import health
    print("✓ Successfully imported routers")
except Exception as e:
    print(f"✗ Failed to import routers: {e}")

print("\nImport test complete!")
