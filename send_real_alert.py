#!/usr/bin/env python3
"""
直接测试真实安全告警 - 使用已配置的飞书 Webhook
"""

import requests
from datetime import datetime

# 飞书 Webhook URL (从之前的配置获取)
FEISHU_WEBHOOK_URL = "https://open.feishu.cn/open-apis/bot/v2/hook/b9607414-c4e4-4ee4-9af7-f1965e503450"

# 真实的 SSH 暴力破解攻击场景
security_alert = {
    'id': 'ALERT-20260224-SSH-BF-001',
    'source': 'wazuh',
    'event_type': 'authentication_failed',
    'severity': 'high',
    'title': '🔒 SSH 暴力破解攻击检测',
    'source_ip': '203.0.113.45',
    'destination_ip': '10.0.0.5',
    'agent_name': 'prod-server-01',
    'rule_id': '5710',
    'rule_level': 12,
    'description': '''**攻击详情**

检测到来自 IP **203.0.113.45** 的暴力破解攻击尝试。

**攻击特征:**
• 在过去 5 分钟内尝试 **15 次** 失败登录
• 使用了 **10 个不同的用户名**
• 来源: 中国北京 (CN)

**目标:**
• 主机: prod-server-01 (10.0.0.5)
• 服务: SSH (端口 22)

**MITRE ATT&CK:**
• T1110 - Brute Force: Password Spraying

**建议措施:**
1. 检查该 IP 的威胁情报
2. 考虑在防火墙中封禁该 IP
3. 监控后续的登录尝试
4. 检查是否有成功的登录''',
    'created_at': datetime.now().isoformat(),
    'event_timestamp': '2026-02-24T21:30:15Z',
    'geoip': 'China, Beijing',
    'attack_attempts': '15'
}

print("=" * 70)
print("🚨 真实安全事件告警测试")
print("   SOC Copilot v0.9.0 - Wazuh SIEM")
print("=" * 70)
print()

print("📋 告警详情:")
print("-" * 70)
print(f"  告警 ID:     {security_alert['id']}")
print(f"  来源:        {security_alert['source']}")
print(f"  事件类型:    {security_alert['event_type']}")
print(f"  严重程度:    🔴 {security_alert['severity'].upper()}")
print(f"  标题:        {security_alert['title']}")
print()
print(f"  攻击者 IP:   {security_alert['source_ip']}")
print(f"  目标主机:    {security_alert['agent_name']} ({security_alert['destination_ip']})")
print(f"  地理位置:    {security_alert['geoip']}")
print(f"  攻击次数:    {security_alert['attack_attempts']} 次")
print(f"  规则 ID:     {security_alert['rule_id']} (Level {security_alert['rule_level']})")
print()

# 构造飞书卡片
color = "orange"  # high severity

feishu_card = {
    "msg_type": "interactive",
    "card": {
        "config": {
            "wide_screen_mode": True
        },
        "header": {
            "title": {
                "content": f"⚠️ [{security_alert['severity'].upper()}] {security_alert['title']}",
                "tag": "plain_text"
            },
            "template": color
        },
        "elements": [
            {
                "tag": "div",
                "text": {
                    "content": f"""**告警详情**

• **告警 ID**: {security_alert['id']}
• **来源**: {security_alert['source'].upper()} SIEM
• **事件类型**: {security_alert['event_type']}
• **严重程度**: 🔴 {security_alert['severity'].upper()}
• **时间**: {security_alert['event_timestamp']}

**网络信息**
• **攻击者 IP**: {security_alert['source_ip']}
• **目标主机**: {security_alert['agent_name']} ({security_alert['destination_ip']})
• **地理位置**: {security_alert['geoip']}

**攻击统计**
• **攻击次数**: {security_alert['attack_attempts']} 次
• **规则 ID**: {security_alert['rule_id']} (Level {security_alert['rule_level']})

{security_alert['description']}""",
                    "tag": "lark_md"
                }
            },
            {
                "tag": "hr"
            },
            {
                "tag": "div",
                "text": {
                    "content": f"🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n🤖 SOC Copilot v0.9.0 | Wazuh SIEM",
                    "tag": "plain_text"
                }
            },
            {
                "tag": "action",
                "actions": [
                    {
                        "tag": "button",
                        "text": {
                            "content": "查看事件详情",
                            "tag": "plain_text"
                        },
                        "type": "primary",
                        "url": f"http://localhost:8000/alerts/{security_alert['id']}"
                    },
                    {
                        "tag": "button",
                        "text": {
                            "content": "封禁 IP",
                            "tag": "plain_text"
                        },
                        "type": "default"
                    }
                ]
            }
        ]
    }
}

print("📤 正在发送告警通知到飞书...")
print()

try:
    response = requests.post(
        FEISHU_WEBHOOK_URL,
        json=feishu_card,
        headers={'Content-Type': 'application/json'},
        timeout=10
    )

    if response.status_code == 200:
        print("✅ 告警通知发送成功！")
        print()
        print("📱 请检查您的飞书群聊")
        print()
        print("您应该收到一条类似这样的告警:")
        print()
        print("┌─────────────────────────────────────────────┐")
        print("│  ⚠️ [HIGH] 🔒 SSH 暴力破解攻击检测          │")
        print("│                                             │")
        print("│  **告警详情**                              │")
        print("│  • 攻击者 IP: 203.0.113.45                 │")
        print("│  • 目标主机: prod-server-01               │")
        print("│  • 攻击次数: 15 次                         │")
        print("│                                             │")
        print("│  [查看事件详情] [封禁 IP]                   │")
        print("└─────────────────────────────────────────────┘")
        print()
        print("=" * 70)
        print("🎉 测试成功")
        print("=" * 70)
        print()
        print("💡 这是真实的安全告警格式示例")
        print("   当 SOC Copilot 与 Wazuh 集成后，")
        print("   所有安全事件都会以这种格式发送到飞书")
        print()

    else:
        print(f"❌ 发送失败: HTTP {response.status_code}")
        print(f"   响应: {response.text}")

except Exception as e:
    print(f"❌ 发送失败: {e}")
    print()
    print("可能的原因:")
    print("  1. Webhook URL 不正确")
    print("  2. 机器人已被移除")
    print("  3. 网络连接问题")
