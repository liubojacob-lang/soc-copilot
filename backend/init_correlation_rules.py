"""Initialize built-in correlation rules.

Run this script to seed the database with default correlation rules.
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from data.correlation_rules_builtin import BUILTIN_CORRELATION_RULES, seed_builtin_rules
from db.session import AsyncSessionLocal
from core.logger import get_logger

logger = get_logger(__name__)


async def main():
    """Initialize built-in correlation rules."""
    print("=" * 60)
    print("🚀 初始化内置关联规则")
    print("=" * 60)
    print()

    async with AsyncSessionLocal() as session:
        try:
            # Seed rules
            count = await seed_builtin_rules(session)

            print(f"\n✅ 成功创建 {count} 条内置规则:")
            print()

            for i, rule_data in enumerate(BUILTIN_CORRELATION_RULES, 1):
                print(f"  {i}. {rule_data['name']}")
                print(f"     时间窗口: {rule_data['time_window_seconds']}秒")
                print(f"     优先级: {rule_data['priority']}")
                print(f"     动作: {rule_data['action']}")
                print()

            print("=" * 60)
            print("✨ 初始化完成！")
            print("=" * 60)

        except Exception as e:
            logger.error(f"Failed to initialize rules: {e}")
            import traceback
            traceback.print_exc()
            return 1

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
