#!/usr/bin/env python
"""Alembic migration helper script."""

import asyncio
import sys
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from alembic.config import Config
from alembic import command


def migrate():
    """Run Alembic migrations."""
    alembic_dir = backend_dir / "migrations_alembic"
    ini_path = backend_dir / "alembic.ini"

    if not alembic_dir.exists():
        print(f"Error: Alembic directory not found: {alembic_dir}")
        sys.exit(1)

    if not ini_path.exists():
        print(f"Error: alembic.ini not found: {ini_path}")
        sys.exit(1)

    config = Config(str(ini_path))
    config.set_main_option("script_location", str(alembic_dir))

    print("Running database migrations...")
    try:
        command.upgrade(config, "head")
        print("Migrations completed successfully!")
    except Exception as e:
        print(f"Migration failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    migrate()
