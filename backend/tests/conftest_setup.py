"""
Test credential constants for auth tests.

All values are generated at runtime by tests/conftest.py (which pytest loads
before any test module) and shared via the environment, so no credential
material lives in source control.
"""

import os

TEST_PASSWORD = os.environ["TEST_PASSWORD"]
TEST_NEW_PASSWORD = os.environ["TEST_NEW_PASSWORD"]
TEST_ALT_PASSWORD = os.environ["TEST_ALT_PASSWORD"]
TEST_WRONG_PASSWORD = os.environ["TEST_WRONG_PASSWORD"]
TEST_MISMATCH_PASSWORD = os.environ["TEST_MISMATCH_PASSWORD"]
TEST_DUMMY_REFRESH_TOKEN = os.environ["TEST_DUMMY_REFRESH_TOKEN"]
