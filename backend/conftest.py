"""
Root conftest.py - sets environment variables before any imports.
This file is loaded by pytest before tests/conftest.py.
"""

import os
import asyncio
import pytest

# Set environment variables BEFORE any other imports
os.environ["ENVIRONMENT"] = "test"
os.environ["BOOTSTRAP_ADMIN_PASSWORD"] = "admin123!TestPass"
os.environ["JWT_SECRET"] = "test-jwt-secret-min-32-characters-long-for-testing"

# Use a separate test database
os.environ["TEST_DB_PATH"] = "/tmp/soc_copilot_test.db"


@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    """Setup test database before all tests and cleanup after."""
    db_path = "/tmp/soc_copilot_test.db"
    
    # Remove old test database if exists
    if os.path.exists(db_path):
        os.remove(db_path)
    
    yield
    
    # Cleanup after all tests
    if os.path.exists(db_path):
        os.remove(db_path)
