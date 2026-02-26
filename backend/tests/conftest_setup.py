"""
Test setup - must be imported before any other imports.
Sets environment variables for testing.
"""

import os
import sys

# Set test environment variables BEFORE any imports
os.environ["ENVIRONMENT"] = "test"
os.environ["BOOTSTRAP_ADMIN_PASSWORD"] = "admin123!TestPass"
os.environ["JWT_SECRET"] = "test-jwt-secret-min-32-characters-long-for-testing"
os.environ["SECRET_ENCRYPTION_KEY"] = "dGVzdC1lbmNyeXB0aW9uLWtleS1mb3ItdGVzdGluZw=="  # Fernet-compatible

# Test password constant
TEST_PASSWORD = "admin123!TestPass"
