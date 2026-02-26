#!/usr/bin/env python3
"""
飞书通知演示 - 展示飞书通知的功能

此脚本演示飞书通知系统的工作流程
"""

import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

print("=" * 70)
print("📱 飞书通知配置演示")
print("   SOC Copilot v0.9.0")
print("=" * 70)
print()

print("🎯 配置飞书通知有两种方式:")
print()

print("方式 1: 交互式配置向导")
print("-" * 70)
print("  在终端中运行以下命令，然后按提示操作:")
print()
print("    $ python configure_feishu.py")
print()
print("  配置向导会引导您:")
print("    ✅ 获取飞书 Webhook URL")
print("    ✅ 验证 URL 格式")
print("    ✅ 保存到 .env 文件")
print("    ✅ 发送测试消息")
print()

print("方式 2: 使用快速测试脚本")
print("-" * 70)
print("  如果您已经有了 Webhook URL，可以直接测试:")
print()
print("    $ python test_feishu_quick.py https://your-webhook-url")
print()
print("  或者保存到配置文件:")
print()
print("    # 添加到 .env 文件")
print("    $ echo 'FEISHU_WEBHOOK_URL=https://your-url' >> .env")
print()
print("    # 然后测试")
print("    $ export FEISHU_WEBHOOK_URL=$(grep FEISHU_WEBHOOK_URL .env | cut -d'=' -f2)")
print("    $ python test_feishu_quick.py $FEISHU_WEBHOOK_URL")
print()

print("=" * 70)
print("📋 如何获取飞书 Webhook URL")
print("=" * 70)
print()

print("步骤 1: 打开飞书客户端")
print("  • 电脑端或移动端都可以")
print()

print("步骤 2: 创建或进入群聊")
print("  • 建议创建专门的安全告警群")
print()

print("步骤 3: 添加自定义机器人")
print("  • 点击群聊右上角的 '...' 或群设置")
print("  • 选择 '群机器人'")
print("  • 点击 '添加机器人'")
print("  • 选择 '自定义机器人'")
print()

print("步骤 4: 配置机器人")
print("  • 机器人名称: SOC Copilot")
print("  • 描述: 安全告警通知 (可选)")
print("  • 头像: 可选")
print()

print("步骤 5: 复制 Webhook URL")
print("  • URL 格式类似:")
print()
print("      https://open.feishu.cn/open-apis/bot/v2/hook/xxx")
print()
print("  • 点击复制按钮")
print("  • 保存这个 URL，后面会用到")
print()

print("=" * 70)
print("🎨 飞书通知消息预览")
print("=" * 70)
print()

print("当配置完成后，您将收到如下格式的告警通知:")
print()

print("┌────────────────────────────────────────┐")
print("│  🚨 安全告警: SSH 登录失败             │")
print("├────────────────────────────────────────┤")
print("│                                        │")
print("│  **告警详情**                          │")
print("│  • 告警 ID: ALERT-001                  │")
print("│  • 来源: Wazuh                          │")
print("│  • 严重程度: 🔴 HIGH                   │")
print("│  • 时间: 2026-02-24 12:00:00           │")
print("│                                        │")
print("│  **网络信息**                          │")
print("│  • 源 IP: 192.168.1.100                │")
print("│  • 目的 IP: 10.0.0.5                   │")
print("│                                        │")
print("│  **主机信息**                          │")
print("│  • 主机名: server-01                   │")
print("│                                        │")
print("│  ──────────────────────────────────  │")
print("│                                        │")
print("│  [查看详情] [关闭]                     │")
print("│                                        │")
print("│  🕐 2026-02-24 12:00:00                │")
print("│  🤖 SOC Copilot v0.9.0                 │")
print("└────────────────────────────────────────┘")
print()

print("=" * 70)
print("🚀 下一步操作")
print("=" * 70)
print()

print("1. 在飞书中获取 Webhook URL")
print("   参考上面的步骤说明")
print()

print("2. 运行配置向导 (推荐)")
print("   $ python configure_feishu.py")
print("   然后粘贴您的 Webhook URL")
print()

print("3. 或使用快速测试")
print("   $ python test_feishu_quick.py https://your-webhook-url")
print()

print("4. 测试成功后，启动服务")
print("   $ docker-compose -f docker-compose.prod.yml up -d")
print()

print("=" * 70)
print("📚 查看更多文档")
print("=" * 70)
print()

print("• FEISHU_QUICKSTART.md - 快速开始指南")
print("• docs/FEISHU_SETUP_GUIDE.md - 完整配置指南")
print("• QUICKSTART_NOTIFICATIONS.md - 通知系统快速开始")
print()

print("=" * 70)
print("✨ 准备好了吗？")
print("=" * 70)
print()

print("当您获取到飞书 Webhook URL 后，运行:")
print()
print("  $ python configure_feishu.py")
print()
print("或者直接测试:")
print()
print("  $ python test_feishu_quick.py <您的Webhook URL>")
print()
