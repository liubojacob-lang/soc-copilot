#!/usr/bin/env python3
"""
飞书通知配置工具
快速配置和测试飞书通知

用法: python configure_feishu.py
"""

import os
import sys
import json
import requests
from datetime import datetime


def print_header():
    """打印标题"""
    print("\n" + "=" * 60)
    print("📱 飞书通知配置向导")
    print("   SOC Copilot v0.9.0")
    print("=" * 60)
    print()


def print_step(step_num, title):
    """打印步骤标题"""
    print(f"\n{step_num}. {title}")
    print("-" * 60)


def get_webhook_url():
    """获取并验证 Webhook URL"""
    print_step(1, "获取飞书 Webhook URL")

    print("\n📋 配置步骤:")
    print("   1. 打开飞书客户端")
    print("   2. 进入要接收告警的群聊")
    print("   3. 点击: 群设置 → 群机器人 → 添加机器人")
    print("   4. 选择「自定义机器人」")
    print("   5. 设置机器人名称: SOC Copilot")
    print("   6. 复制生成的 Webhook URL")

    print("\n📝 URL 格式示例:")
    print("   https://open.feishu.cn/open-apis/bot/v2/hook/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx")

    while True:
        print("\n" + "=" * 60)
        webhook_url = input("请粘贴您的飞书 Webhook URL: ").strip()

        # 验证 URL
        if not webhook_url:
            print("❌ URL 不能为空，请重新输入")
            continue

        if not webhook_url.startswith("https://open.feishu.cn/open-apis/bot/v2/hook/"):
            print("❌ URL 格式不正确")
            print("   应该以: https://open.feishu.cn/open-apis/bot/v2/hook/ 开头")
            continue

        print("\n✅ URL 格式验证通过")
        return webhook_url


def save_to_env(webhook_url):
    """保存到 .env 文件"""
    print_step(2, "保存配置")

    env_file = ".env"
    backup_file = ".env.backup"

    # 检查 .env 是否存在
    if os.path.exists(env_file):
        print(f"\n📄 找到现有配置文件: {env_file}")
        choice = input("是否更新现有配置? (y/n): ").lower()

        if choice != 'y':
            print("⏭️  跳过保存配置")
            return False

        # 备份现有配置
        if os.path.exists(backup_file):
            os.remove(backup_file)
        os.rename(env_file, backup_file)
        print(f"💾 已备份现有配置到: {backup_file}")

    # 读取或创建配置
    config_lines = []
    if os.path.exists(backup_file):
        with open(backup_file, 'r') as f:
            config_lines = f.readlines()

        # 更新或添加 FEISHU_WEBHOOK_URL
        updated = False
        for i, line in enumerate(config_lines):
            if line.startswith("FEISHU_WEBHOOK_URL="):
                config_lines[i] = f"FEISHU_WEBHOOK_URL={webhook_url}\n"
                updated = True
                break

        if not updated:
            config_lines.append(f"\n# 飞书通知配置\n")
            config_lines.append(f"FEISHU_WEBHOOK_URL={webhook_url}\n")
    else:
        # 使用通知配置模板
        template_file = ".env.notifications.example"
        if os.path.exists(template_file):
            with open(template_file, 'r') as f:
                config_lines = f.readlines()

            # 替换示例 URL
        for i, line in enumerate(config_lines):
            if line.startswith("#FEISHU_WEBHOOK_URL="):
                config_lines[i] = f"FEISHU_WEBHOOK_URL={webhook_url}\n"
            elif line.startswith("FEISHU_WEBHOOK_URL="):
                config_lines[i] = f"FEISHU_WEBHOOK_URL={webhook_url}\n"
        else:
            # 创建新配置
            config_lines = [
                "# SOC Copilot 配置\n",
                "# 飞书通知配置\n",
                f"FEISHU_WEBHOOK_URL={webhook_url}\n",
            ]

    # 保存配置
    with open(env_file, 'w') as f:
        f.writelines(config_lines)

    print(f"\n✅ 配置已保存到: {env_file}")
    return True


def send_test_message(webhook_url):
    """发送测试消息"""
    print_step(3, "测试飞书通知")

    print("\n📤 正在发送测试消息...")
    print()

    # 构造测试卡片
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

**下一步**
1. 启动 SOC Copilot 服务
2. 配置更多通知渠道 (Slack/Email)
3. 测试告警流程""",
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
                }
            ]
        }
    }

    # 发送消息
    try:
        response = requests.post(
            webhook_url,
            json=test_card,
            headers={'Content-Type': 'application/json'},
            timeout=10
        )

        if response.status_code == 200:
            print("✅ 测试消息发送成功！")
            print("\n📱 请检查您的飞书群聊，应该已收到一条测试消息。")
            return True
        else:
            print(f"❌ 发送失败: HTTP {response.status_code}")
            print(f"   响应: {response.text}")
            return False

    except requests.exceptions.Timeout:
        print("❌ 请求超时")
        print("   请检查网络连接")
        return False
    except requests.exceptions.RequestException as e:
        print(f"❌ 发送失败: {e}")
        print("   请检查:")
        print("   1. Webhook URL 是否正确")
        print("   2. 网络连接是否正常")
        return False


def show_next_steps(webhook_url, saved):
    """显示后续步骤"""
    print_step(4, "配置完成")

    print("\n🎉 飞书通知配置完成！")

    if saved:
        print("\n✅ 配置已保存，下次启动会自动加载")

    print("\n📋 后续步骤:")

    print("\n1️⃣  配置环境变量 (如果尚未保存)")
    print(f"   export FEISHU_WEBHOOK_URL={webhook_url}")

    print("\n2️⃣  启动 SOC Copilot 服务")
    print("   docker-compose -f docker-compose.prod.yml up -d")

    print("\n3️⃣  发送测试告警")
    print("   curl -X POST http://localhost:8000/api/v1/security-alerts/ingest \\")
    print("     -H 'Content-Type: application/json' \\")
    print("     -d '{")
    print('       "source":"test",')
    print('       "event_id":"test-001",')
    print('       "event_type":"test",')
    print('       "severity":"high",')
    print('       "title":"测试告警",')
    print('       "description":"这是一条测试告警",')
    print('       "timestamp":"2026-02-24T12:00:00Z"')
    print("     }'")

    print("\n4️⃣  配置更多通知渠道 (推荐)")
    print("   - Slack: 提高海外团队可访问性")
    print("   - Email: 离线通知和归档")

    print("\n📚 查看文档:")
    print("   - docs/FEISHU_SETUP_GUIDE.md - 飞书配置详细指南")
    print("   - QUICKSTART_NOTIFICATIONS.md - 快速开始指南")
    print("   - IMPLEMENTATION_REPORT.md - 完整实施报告")

    print("\n" + "=" * 60)


def main():
    """主函数"""
    print_header()

    try:
        # 获取 Webhook URL
        webhook_url = get_webhook_url()

        # 保存配置
        print("\n" + "=" * 60)
        choice = input("\n是否保存配置到 .env 文件? (y/n): ").lower()
        saved = False

        if choice == 'y':
            saved = save_to_env(webhook_url)

        # 测试通知
        print("\n" + "=" * 60)
        test_choice = input("\n是否发送测试消息? (y/n): ").lower()

        if test_choice == 'y':
            success = send_test_message(webhook_url)

            if not success:
                print("\n⚠️  测试消息发送失败")
                print("   请检查 Webhook URL 是否正确")
                print("   然后重试或联系技术支持")
                return 1

        # 显示后续步骤
        show_next_steps(webhook_url, saved)

        print("\n✨ 配置完成！")
        return 0

    except KeyboardInterrupt:
        print("\n\n❌ 配置已取消")
        return 1
    except Exception as e:
        print(f"\n\n❌ 发生错误: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
