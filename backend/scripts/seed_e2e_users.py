"""Seed E2E test users (admin, analyst, auditor) with valid bcrypt passwords.

Usage:
    cd backend
    python scripts/seed_e2e_users.py
"""

import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select

from core.security import get_password_hash
from db.session import AsyncSessionLocal
from models.user import UserModel, UserRole

E2E_USERS = [
    {
        "username": os.getenv("E2E_ADMIN_USERNAME", "admin"),
        "password": os.getenv("E2E_ADMIN_PASSWORD", "admin123"),
        "email": "admin@soc-copilot.local",
        "role": UserRole.ADMIN.value,
    },
    {
        "username": os.getenv("E2E_ANALYST_USERNAME", "analyst"),
        "password": os.getenv("E2E_ANALYST_PASSWORD", "analyst123"),
        "email": "analyst@soc-copilot.local",
        "role": UserRole.ANALYST.value,
    },
    {
        "username": os.getenv("E2E_AUDITOR_USERNAME", "auditor"),
        "password": os.getenv("E2E_AUDITOR_PASSWORD", "auditor123"),
        "email": "auditor@soc-copilot.local",
        "role": UserRole.AUDITOR.value,
    },
]


async def seed_users():
    async with AsyncSessionLocal() as session:
        for u in E2E_USERS:
            stmt = select(UserModel).where(UserModel.username == u["username"])
            user = (await session.scalars(stmt)).first()
            hashed = get_password_hash(u["password"])
            if user:
                user.hashed_password = hashed
                user.role = u["role"]
                user.must_change_password = False
                user.is_active = True
                print(f"Updated user: {u['username']} (role: {u['role']})")
            else:
                user = UserModel(
                    username=u["username"],
                    email=u["email"],
                    hashed_password=hashed,
                    role=u["role"],
                    must_change_password=False,
                    is_active=True,
                )
                session.add(user)
                print(f"Created user: {u['username']} (role: {u['role']})")
        await session.commit()
    print("E2E test users seeded successfully.")


if __name__ == "__main__":
    asyncio.run(seed_users())
