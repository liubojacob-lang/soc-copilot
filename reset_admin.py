#!/usr/bin/env python3
"""
重置 admin 用户密码和解锁账户
"""

import asyncio
import sys
import os

# 添加 backend 到路径
backend_dir = os.path.join(os.path.dirname(__file__), 'backend')
sys.path.insert(0, backend_dir)

os.chdir(backend_dir)

from sqlalchemy import select
from db.session import AsyncSessionLocal
from models.user import UserModel
from core.security import get_password_hash


async def reset_admin():
    """重置 admin 用户"""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(UserModel).where(UserModel.username == 'admin')
        )
        user = result.scalar_one_or_none()

        if user:
            # 重置密码为 admin123
            new_password = "admin123"
            user.hashed_password = get_password_hash(new_password)
            user.locked_until = None

            await session.commit()

            print(f"✓ admin 用户已重置")
            print(f"  新密码: {new_password}")
            print(f"  用户已解锁")
            return True
        else:
            print("✗ 未找到 admin 用户")
            return False


if __name__ == "__main__":
    asyncio.run(reset_admin())
