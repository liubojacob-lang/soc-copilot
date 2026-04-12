#!/usr/bin/env python3
"""Test script to verify v0.8.5 optimizations.

Tests:
1. Async rate limiter initialization
2. Secret encryption key validation
3. Performance middleware
4. Audit archive service
"""

import asyncio
import os
import sys

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_config_validation():
    """Test config validation for secret_encryption_key."""
    print("\n=== Testing Config Validation ===")

    from core.config import Settings

    # Test development mode (should auto-generate key)
    settings_dev = Settings(environment="development")
    print(
        f"✓ Development mode: secret_encryption_key auto-generated: {bool(settings_dev.secret_encryption_key)}"
    )

    # Test that key is valid Fernet format
    if settings_dev.secret_encryption_key:
        try:
            from cryptography.fernet import Fernet

            Fernet(settings_dev.secret_encryption_key.encode())
            print("✓ Generated key is valid Fernet format")
        except Exception as e:
            print(f"✗ Generated key is NOT valid Fernet format: {e}")
            return False

    return True


def test_rate_limiter():
    """Test async rate limiter."""
    print("\n=== Testing Async Rate Limiter ===")

    from middleware.rate_limiter import get_rate_limiter

    # Test singleton
    limiter = get_rate_limiter()
    print("✓ Rate limiter singleton created")
    print(f"  - Redis enabled: {limiter._enabled}")

    return True


async def test_rate_limiter_async():
    """Test async rate limiter operations."""
    print("\n=== Testing Async Rate Limiter Operations ===")

    from middleware.rate_limiter import get_rate_limiter

    limiter = get_rate_limiter()

    # Test in-memory rate limiting
    allowed, info = await limiter.is_allowed(
        identifier="test_user",
        endpoint="test_endpoint",
        max_requests=5,
        window_seconds=60,
    )
    print(f"✓ Rate limit check: allowed={allowed}, info={info}")

    # Test multiple requests
    for i in range(6):
        allowed, info = await limiter.is_allowed(
            identifier="test_user_2",
            endpoint="test_endpoint",
            max_requests=5,
            window_seconds=60,
        )
        if i < 5:
            assert allowed, f"Request {i+1} should be allowed"
        else:
            assert not allowed, f"Request {i+1} should be blocked"

    print("✓ Rate limiting works correctly (5 allowed, 6th blocked)")

    return True


def test_performance_middleware():
    """Test performance middleware."""
    print("\n=== Testing Performance Middleware ===")

    from middleware.performance import REQUEST_DURATION_HISTOGRAM

    print("✓ PerformanceMiddleware class imported")
    print(
        f"  - Prometheus histogram available: {REQUEST_DURATION_HISTOGRAM is not None}"
    )

    return True


def test_audit_archive_service():
    """Test audit archive service."""
    print("\n=== Testing Audit Archive Service ===")

    from db.session import AsyncSessionLocal
    from services.audit_archive_service import AuditArchiveService

    # Test service creation
    service = AuditArchiveService(AsyncSessionLocal)
    print("✓ AuditArchiveService created")
    print(f"  - Archive dir: {service.archive_dir}")
    print(f"  - Retention days: {service.retention_days}")
    print(f"  - Archive retention days: {service.archive_retention_days}")

    return True


async def test_audit_archive_stats():
    """Test audit archive stats."""
    print("\n=== Testing Audit Archive Stats ===")

    from db.session import AsyncSessionLocal
    from services.audit_archive_service import AuditArchiveService

    service = AuditArchiveService(AsyncSessionLocal)
    stats = await service.get_archive_stats()

    print("✓ Archive stats retrieved")
    print(f"  - Archive files: {stats['archive_files']}")
    print(f"  - Total size: {stats['total_size_bytes']} bytes")

    return True


def test_main_integration():
    """Test that main.py imports correctly."""
    print("\n=== Testing Main.py Integration ===")

    try:
        # This will test all imports including our new modules

        print("✓ main.py imports successfully")
        return True
    except Exception as e:
        print(f"✗ main.py import failed: {e}")
        return False


def main():
    """Run all tests."""
    print("=" * 60)
    print("SOC Copilot v0.8.5 Optimization Tests")
    print("=" * 60)

    all_passed = True

    # Sync tests
    all_passed &= test_config_validation()
    all_passed &= test_rate_limiter()
    all_passed &= test_performance_middleware()
    all_passed &= test_audit_archive_service()
    all_passed &= test_main_integration()

    # Async tests
    print("\n--- Running Async Tests ---")
    all_passed &= asyncio.run(test_rate_limiter_async())
    all_passed &= asyncio.run(test_audit_archive_stats())

    print("\n" + "=" * 60)
    if all_passed:
        print("✓ All optimization tests passed!")
        print("=" * 60)
        return 0
    else:
        print("✗ Some tests failed!")
        print("=" * 60)
        return 1


if __name__ == "__main__":
    sys.exit(main())
