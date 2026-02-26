#!/usr/bin/env python3
"""测试 Loki 集成 - 发送测试告警到 Grafana Loki"""

import asyncio
import sys
sys.path.insert(0, 'backend')

from services.loki_alert_sender import get_loki_sender


async def main():
    """主函数"""
    print("=== SOC Copilot → Loki 集成测试 ===\n")
    
    # 获取 Loki 发送器
    sender = get_loki_sender()
    
    # 发送测试告警
    print("1. 发送测试告警到 Loki...")
    success = await sender.send_test_alert()
    
    if success:
        print("✅ 测试告警发送成功！\n")
        print("2. 请在 Grafana 中查看:")
        print("   - 访问: http://localhost:3001")
        print("   - 用户名/密码: admin/admin")
        print("   - 进入: Explore → Loki")
        print("   - 查询: {job=\"soc-copilot\"}")
        print("   - 应该能看到测试告警\n")
    else:
        print("❌ 测试告警发送失败\n")
    
    # 关闭发送器
    await sender.close()
    
    print("测试完成！")


if __name__ == "__main__":
    asyncio.run(main())
