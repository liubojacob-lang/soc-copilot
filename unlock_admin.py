#!/usr/bin/env python3
"""
解锁 admin 用户脚本
"""

import asyncio
import sys
sys.path.insert(0, 'backend')

from sqlalchemy import select
from backend.db.session import AsyncSessionLocal
from backend.models.user import UserModel


async def unlock_admin():
    """解锁 admin 用户"""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(UserModel).where(UserModel.username == 'admin')
        )
        user = result.scalar_one_or_none()

        if user:
            print(f'找到用户: {user.username}')
            print(f'当前锁定状态: {user.locked_until}')

            # 解锁用户
            user.locked_until = None
            await session.commit()

            print('✓ 用户已解锁！现在可以登录了')
            return True
        else:
            print('✗ 未找到 admin 用户')
            return False


if __name__ == "__main__":
    asyncio.run(unlock_admin())
