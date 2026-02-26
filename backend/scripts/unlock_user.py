#!/usr/bin/env python3
"""
解锁被锁定的用户账户
用法: python unlock_user.py <username>
"""

import asyncio
import sys
import os

# 添加 backend 目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from db.session import AsyncSessionLocal
from models.user import UserModel


async def unlock_user(username: str):
    """解锁指定用户"""
    async with AsyncSessionLocal() as session:
        # 查找用户
        result = await session.execute(
            select(UserModel).where(UserModel.username == username)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            print(f"❌ 用户 '{username}' 不存在")
            return False
        
        if not user.locked_until:
            print(f"✅ 用户 '{username}' 未被锁定")
            return True
        
        # 清除锁定状态
        user.failed_login_attempts = 0
        user.locked_until = None
        await session.commit()
        
        print(f"✅ 用户 '{username}' 已成功解锁")
        return True


async def unlock_all_users():
    """解锁所有被锁定的用户"""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(UserModel).where(UserModel.locked_until.isnot(None))
        )
        locked_users = result.scalars().all()
        
        if not locked_users:
            print("✅ 没有被锁定的用户")
            return
        
        for user in locked_users:
            user.failed_login_attempts = 0
            user.locked_until = None
            print(f"🔓 解锁用户: {user.username}")
        
        await session.commit()
        print(f"\n✅ 已解锁 {len(locked_users)} 个用户")


def main():
    if len(sys.argv) < 2:
        print("用法:")
        print("  python unlock_user.py <username>  # 解锁指定用户")
        print("  python unlock_user.py --all       # 解锁所有用户")
        sys.exit(1)
    
    if sys.argv[1] == "--all":
        asyncio.run(unlock_all_users())
    else:
        username = sys.argv[1]
        asyncio.run(unlock_user(username))


if __name__ == "__main__":
    main()
