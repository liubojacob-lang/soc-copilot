#!/usr/bin/env python3
"""Unlock a user account."""
import asyncio
import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_dir))

from sqlalchemy.ext.asyncio import AsyncSession
from db.session import get_session
from repositories.user_repository import UserRepository


async def unlock_user(username: str):
    """Unlock a user account."""
    async for session in get_session():
        try:
            user_repo = UserRepository(session)
            user = await user_repo.get_by_username(username)

            if not user:
                print(f"❌ User '{username}' not found")
                return

            print(f"📋 User: {user.username}")
            print(f"📧 Email: {user.email}")
            print(f"🔒 Failed attempts: {user.failed_login_attempts or 0}")
            print(f"⏰ Locked until: {user.locked_until}")

            # Clear lockout
            user.failed_login_attempts = 0
            user.locked_until = None

            await session.commit()

            print(f"\n✅ Account '{username}' has been unlocked!")
            print(f"   You can now login again.")

        except Exception as e:
            print(f"❌ Error: {e}")
            await session.rollback()
            raise


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python unlock_user.py <username>")
        print("Example: python unlock_user.py admin")
        sys.exit(1)

    username = sys.argv[1]
    asyncio.run(unlock_user(username))
