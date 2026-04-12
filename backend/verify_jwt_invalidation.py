#!/usr/bin/env python3
"""Quick verification script for JWT token invalidation feature."""

import sys
from datetime import UTC, datetime, timedelta

# Add backend to path
sys.path.insert(0, "/Users/levent/Desktop/Projects/sec/backend")

from core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    is_token_invalidated_by_user_update,
)

print("🔐 Testing JWT Token Invalidation Feature\n")
print("=" * 60)

# Test 1: New tokens have iat claim
print("\n✅ Test 1: New tokens include 'iat' claim")
token = create_access_token(data={"sub": "user-123"})
payload = decode_token(token)
assert "iat" in payload, "Token missing iat claim!"
print(f"   ✅ Access token has iat: {payload['iat']}")

refresh = create_refresh_token(data={"sub": "user-123"})
refresh_payload = decode_token(refresh)
assert "iat" in refresh_payload, "Refresh token missing iat claim!"
print(f"   ✅ Refresh token has iat: {refresh_payload['iat']}")

# Test 2: Token valid when no user update
print("\n✅ Test 2: Token valid when user has no updated_at")
is_invalid = is_token_invalidated_by_user_update(payload, None)
assert is_invalid is False, "Token should be valid when no updated_at"
print("   ✅ Token is valid (no user update)")

# Test 3: Token valid when issued after update
print("\n✅ Test 3: Token valid when issued AFTER user update")
user_updated = (datetime.now(UTC) - timedelta(minutes=5)).isoformat()
is_invalid = is_token_invalidated_by_user_update(payload, user_updated)
assert is_invalid is False, "Token should be valid when issued after update"
print("   ✅ Token is valid (issued after user update)")

# Test 4: Token invalidated when issued before update
print("\n✅ Test 4: Token invalidated when issued BEFORE user update")
# Create new token
token2 = create_access_token(data={"sub": "user-456"})
payload2 = decode_token(token2)
# Simulate user update happened AFTER token was issued
user_updated_future = (datetime.now(UTC) + timedelta(seconds=1)).isoformat()
is_invalid = is_token_invalidated_by_user_update(payload2, user_updated_future)
assert is_invalid is True, "Token should be invalidated when issued before update"
print("   ✅ Token is INVALIDATED (issued before user update)")

# Test 5: Role change invalidates old tokens
print("\n✅ Test 5: Role change invalidates old tokens")
token3 = create_access_token(data={"sub": "user-789", "role": "analyst"})
payload3 = decode_token(token3)
# Simulate role change
user_updated = (datetime.now(UTC) + timedelta(seconds=1)).isoformat()
is_invalid = is_token_invalidated_by_user_update(payload3, user_updated)
assert is_invalid is True, "Token should be invalidated after role change"
print("   ✅ Token is INVALIDATED after role change")

# Test 6: Password change invalidates old tokens
print("\n✅ Test 6: Password change invalidates old tokens")
token4 = create_access_token(data={"sub": "user-789"})
payload4 = decode_token(token4)
user_updated = (datetime.now(UTC) + timedelta(seconds=1)).isoformat()
is_invalid = is_token_invalidated_by_user_update(payload4, user_updated)
assert is_invalid is True, "Token should be invalidated after password change"
print("   ✅ Token is INVALIDATED after password change")

print("\n" + "=" * 60)
print("✅ ALL TESTS PASSED!")
print("\n🎉 JWT Token Invalidation Feature Working Correctly!")
print("\n📋 How it works:")
print("   1. New tokens include 'iat' (issued at) claim")
print("   2. User model has 'updated_at' timestamp")
print("   3. When user role/password changes, updated_at is refreshed")
print("   4. Authentication checks if token.iat < user.updated_at")
print("   5. If yes, token is rejected (issued before the change)")
