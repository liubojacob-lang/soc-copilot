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

    print("✓ Successfully imported core.config")
except Exception as e:
    print(f"✗ Failed to import core.config: {e}")

try:

    print("✓ Successfully imported core.logger")
except Exception as e:
    print(f"✗ Failed to import core.logger: {e}")

try:

    print("✓ Successfully imported db.session")
except Exception as e:
    print(f"✗ Failed to import db.session: {e}")

try:

    print("✓ Successfully imported routers")
except Exception as e:
    print(f"✗ Failed to import routers: {e}")

print("\nImport test complete!")
