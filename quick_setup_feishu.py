#!/usr/bin/env python3
"""
快速配置飞书通知 - 使用命令行参数
"""

import sys
import os
import requests
from datetime import datetime


def main():
    webhook_url = "https://open.feishu.cn/open-apis/bot/v2/hook/b9607414-c4e4-4ee4-9af7-f1965e503450"

    print("=" * 70)
    print("📱 飞书通知快速配置")
    print("   SOC Copilot v0.9.0")
    print("=" * 70)
    print()

    # 验证 URL
    print("📋 Webhook URL:")
    print(f"   {webhook_url[:50]}...")
    print()

    if webhook_url.startswith("https://open.feishu.cn/open-apis/bot/v2/hook/"):
        print("✅ URL 格式验证通过")
    else:
        print("❌ URL 格式不正确")
        return 1

    print()

    # 保存到 .env 文件
    print("💾 保存配置...")
    env_file = ".env"
    backup_file = ".env.backup"

    try:
        # 备份现有配置
        if os.path.exists(env_file):
            if os.path.exists(backup_file):
                os.remove(backup_file)
            os.rename(env_file, backup_file)
            print(f"   已备份现有配置到: {backup_file}")

        # 读取或创建配置
        config_lines = []
        if os.path.exists(backup_file):
            with open(backup_file, 'r', encoding='utf-8') as f:
                config_lines = f.readlines()

        # 更新或添加 FEISHU_WEBHOOK_URL
        updated = False
        for i, line in enumerate(config_lines):
            if line.startswith("FEISHU_WEBHOOK_URL="):
                config_lines[i] = f"FEISHU_WEBHOOK_URL={webhook_url}\n"
                updated = True
                break

        if not updated:
            if config_lines and not config_lines[-1].endswith('\n'):
                config_lines.append('\n')
            config_lines.append(f"\n# 飞书通知配置\n")
            config_lines.append(f"FEISHU_WEBHOOK_URL={webhook_url}\n")

        # 保存配置
        with open(env_file, 'w', encoding='utf-8') as f:
            f.writelines(config_lines)

        print(f"   ✅ 配置已保存到: {env_file}")

    except Exception as e:
        print(f"   ❌ 保存失败: {e}")
        return 1

    print()

    # 发送测试消息
    print("📤 发送测试消息...")
    print()

    test_card = {
        "msg_type": "interactive",
        "card": {
            "config": {
                "wide_screen_mode": True
            },
            "header": {
                "title": {
                    "content": "✅ 飞书通知配置成功！",
                    "tag": "plain_text"
                },
                "template": "green"
            },
            "elements": [
                {
                    "tag": "div",
                    "text": {
                        "content": f"""**SOC Copilot 安全告警系统**

恭喜！您已成功配置飞书通知。

当系统检测到安全威胁时，您将在此群聊中收到实时告警通知。

**配置信息**
• 通知类型: 飞书自定义机器人
• 配置时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
• 系统版本: SOC Copilot v0.9.0

**通知示例**
您将收到类似这样的告警:
• 🚨 安全告警: SSH 登录失败
• ⚠️ 安全告警: 恶意文件检测
• 📊 安全告警: 异常网络连接

**下一步**
1. 启动 SOC Copilot 服务
2. 配置更多通知渠道 (Slack/Email)
3. 测试完整告警流程""",
                        "tag": "lark_md"
                    }
                },
                {
                    "tag": "hr"
                },
                {
                    "tag": "div",
                    "text": {
                        "content": f"📅 测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n🤖 SOC Copilot v0.9.0",
                        "tag": "plain_text"
                    }
                },
                {
                    "tag": "hr"
                },
                {
                    "tag": "div",
                    "text": {
                        "content": "💡 提示: 建议同时配置 Slack 或 Email 作为备用通知渠道",
                        "tag": "plain_text"
                    }
                }
            ]
        }
    }

    try:
        response = requests.post(
            webhook_url,
            json=test_card,
            headers={'Content-Type': 'application/json'},
            timeout=10
        )

        if response.status_code == 200:
            print("   ✅ 测试消息发送成功！")
            print()
            print("   📱 请检查您的飞书群聊，应该已收到测试消息")
            print()
        else:
            print(f"   ❌ 发送失败: HTTP {response.status_code}")
            print(f"   响应: {response.text}")
            return 1

    except Exception as e:
        print(f"   ❌ 发送失败: {e}")
        print()
        print("   可能的原因:")
        print("   1. Webhook URL 不正确")
        print("   2. 网络连接问题")
        print("   3. 机器人已被移除")
        return 1

    print()
    print("=" * 70)
    print("🎉 飞书通知配置完成！")
    print("=" * 70)
    print()
    print("📋 后续步骤:")
    print()
    print("1️⃣  启动 SOC Copilot 服务")
    print("   docker-compose -f docker-compose.prod.yml up -d")
    print()
    print("2️⃣  发送测试告警")
    print("   curl -X POST http://localhost:8000/api/v1/security-alerts/ingest \\")
    print("     -H 'Content-Type: application/json' \\")
    print('     -d \'{"source":"test","event_id":"test-001","event_type":"test","severity":"high","title":"测试告警","description":"这是一条测试告警","timestamp":"2026-02-24T12:00:00Z"}\'')
    print()
    print("3️⃣  配置环境变量 (如果需要)")
    print(f"   export FEISHU_WEBHOOK_URL={webhook_url}")
    print()
    print("📚 查看文档:")
    print("   - FEISHU_QUICK_REF.md - 快速参考")
    print("   - docs/FEISHU_SETUP_GUIDE.md - 完整指南")
    print()

    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n❌ 配置已取消")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ 发生错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
