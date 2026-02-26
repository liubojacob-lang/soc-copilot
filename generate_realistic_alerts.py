#!/usr/bin/env python3
"""
生成真实环境的安全告警数据
模拟 SOC 环境中的各种攻击场景
"""

import random
import time
import json
from datetime import datetime, timedelta
from typing import List, Dict
import requests

# ==================== 配置 ====================
LOKI_URL = "http://localhost:3100/loki/api/v1/push"
TOTAL_ALERTS = 500  # 总告警数量
TIME_SPAN_HOURS = 24  # 时间跨度（小时）

# ==================== 真实攻击场景 ====================
ATTACK_SCENARIOS = {
    "ssh_bruteforce": {
        "weight": 25,  # 权重
        "levels": ["high", "critical"],
        "templates": [
            {
                "message": "SSH brute force attack detected from {src_ip}",
                "details": {
                    "attack_type": "ssh_bruteforce",
                    "username": ["root", "admin", "ubuntu", "test", "user"],
                    "attempts": [50, 100, 200, 500],
                    "duration": ["5m", "10m", "30m"]
                }
            }
        ]
    },
    "port_scan": {
        "weight": 20,
        "levels": ["medium", "high"],
        "templates": [
            {
                "message": "Port scan detected from {src_ip}",
                "details": {
                    "attack_type": "port_scan",
                    "scan_type": ["TCP SYN", "TCP Connect", "UDP", "XMAS"],
                    "scanned_ports": [[22, 80, 443], [21, 22, 23, 25, 53, 80, 110, 143, 443, 3306, 3389, 5432]],
                    "duration": ["1s", "5s", "30s"]
                }
            }
        ]
    },
    "malware_detected": {
        "weight": 15,
        "levels": ["critical"],
        "templates": [
            {
                "message": "Malware signature detected: {malware_name}",
                "details": {
                    "attack_type": "malware",
                    "malware_name": ["Trojan.Generic", "WannaCry", "Emotet", "TrickBot", "Mirai Botnet"],
                    "file_path": ["/tmp/.hidden", "/var/tmp/upload.exe", "/home/user/Downloads/document.pdf.exe"],
                    "action": ["quarantined", "blocked", "deleted"]
                }
            }
        ]
    },
    "sql_injection": {
        "weight": 12,
        "levels": ["high", "critical"],
        "templates": [
            {
                "message": "SQL injection attempt detected on {dst_ip}",
                "details": {
                    "attack_type": "sql_injection",
                    "payload": ["' OR '1'='1", "1' UNION SELECT NULL--", "'; DROP TABLE users--"],
                    "endpoint": ["/api/login", "/api/users", "/admin/auth"],
                    "method": ["POST", "GET"]
                }
            }
        ]
    },
    "ddos_attack": {
        "weight": 10,
        "levels": ["critical"],
        "templates": [
            {
                "message": "DDoS attack detected - {requests_per_sec} req/s from {src_ip}",
                "details": {
                    "attack_type": "ddos",
                    "requests_per_sec": [1000, 5000, 10000, 50000],
                    "target": ["Web Server", "API Gateway", "Load Balancer"],
                    "duration": ["5m", "15m", "1h"]
                }
            }
        ]
    },
    "xss_attempt": {
        "weight": 8,
        "levels": ["medium", "high"],
        "templates": [
            {
                "message": "Cross-site scripting (XSS) attempt detected",
                "details": {
                    "attack_type": "xss",
                    "payload": ["<script>alert('XSS')</script>", "<img src=x onerror=alert('XSS')>"],
                    "endpoint": ["/search", "/comment", "/profile"]
                }
            }
        ]
    },
    "brute_force_web": {
        "weight": 10,
        "levels": ["medium", "high"],
        "templates": [
            {
                "message": "Web application brute force on {endpoint}",
                "details": {
                    "attack_type": "web_bruteforce",
                    "endpoint": ["/login", "/admin", "/api/auth"],
                    "attempts": [20, 50, 100],
                    "user_agent": ["sqlmap", "nikto", "burp", "custom-script"]
                }
            }
        ]
    }
}

# ==================== 真实 IP 地址池 ====================
SOURCE_IPS = {
    "internal": [
        "192.168.1.100", "192.168.1.101", "192.168.1.102",
        "10.0.0.50", "10.0.0.51", "10.0.0.52",
        "172.16.0.10", "172.16.0.11"
    ],
    "external": [
        "45.33.32.156", "104.238.140.39", "159.89.195.232",
        "206.189.123.45", "139.59.1.100", "178.128.0.1",
        "51.15.140.22", "167.99.100.50", "185.200.11.22",
        "89.101.120.50", "210.50.30.100"
    ],
    "malicious": [
        "103.10.60.200", "185.220.101.1", "185.220.101.2",
        "199.87.154.255", "199.87.154.253", "154.53.35.102"
    ]
}

AGENT_IDS = [
    "agent-001", "agent-002", "agent-003", "agent-004",
    "agent-005", "agent-006", "web-server-01", "web-server-02",
    "db-server-01", "cache-server-01"
]

# ==================== 辅助函数 ====================
def get_timestamp_ns(offset_seconds: int = 0) -> str:
    """获取纳秒级时间戳"""
    ts = datetime.now() - timedelta(seconds=offset_seconds)
    return str(int(ts.timestamp() * 1_000_000_000))

def select_weighted(scenarios: Dict) -> str:
    """根据权重选择攻击场景"""
    choices = []
    weights = []
    for name, config in scenarios.items():
        choices.append(name)
        weights.append(config["weight"])
    return random.choices(choices, weights=weights, k=1)[0]

def get_random_ip() -> str:
    """获取随机源 IP"""
    rand = random.random()
    if rand < 0.6:
        return random.choice(SOURCE_IPS["external"])
    elif rand < 0.9:
        return random.choice(SOURCE_IPS["internal"])
    else:
        return random.choice(SOURCE_IPS["malicious"])

def format_template(template: str, **kwargs) -> str:
    """格式化模板字符串"""
    return template.format(**kwargs)

def generate_alert(alert_id: int, time_offset: int) -> Dict:
    """生成单个告警"""

    # 选择攻击场景
    scenario_name = select_weighted(ATTACK_SCENARIOS)
    scenario = ATTACK_SCENARIOS[scenario_name]

    # 选择严重级别
    level = random.choice(scenario["levels"])

    # 选择模板
    template = random.choice(scenario["templates"])

    # 生成详细信息
    src_ip = get_random_ip()
    agent_id = random.choice(AGENT_IDS)

    details = {
        "alert_id": alert_id,
        "timestamp": datetime.now().isoformat(),
        "scenario": scenario_name,
        "src_ip": src_ip,
        "dst_ip": random.choice(SOURCE_IPS["internal"]) if random.random() > 0.3 else src_ip,
        "agent_id": agent_id,
        "geoip": {
            "country": random.choice(["US", "CN", "RU", "BR", "DE", "FR", "UK", "IN"]),
            "city": random.choice(["New York", "Beijing", "Moscow", "São Paulo", "Berlin", "Paris", "London", "Mumbai"])
        },
        "protocol": random.choice(["TCP", "UDP", "HTTP", "HTTPS"])
    }

    # 填充模板详情
    if "details" in template:
        for key, values in template["details"].items():
            if isinstance(values, list):
                details[key] = random.choice(values)
            else:
                details[key] = values

    # 生成消息
    message = format_template(
        template["message"],
        src_ip=src_ip,
        dst_ip=details.get("dst_ip", "N/A"),
        malware_name=details.get("malware_name", "Unknown"),
        requests_per_sec=details.get("requests_per_sec", 0),
        endpoint=details.get("endpoint", "/")
    )

    # 根据攻击类型调整告警
    if scenario_name == "ssh_bruteforce":
        details.update({
            "service": "ssh",
            "port": 22,
            "protocol": "TCP"
        })
    elif scenario_name == "port_scan":
        details.update({
            "ports_scanned": len(details.get("scanned_ports", [])),
            "scan_duration": details.get("duration", "unknown")
        })
    elif scenario_name == "malware_detected":
        details.update({
            "file_hash": "".join([random.choice("0123456789abcdef") for _ in range(64)]),
            "quarantine_status": details.get("action", "unknown")
        })

    alert = {
        "job": "soc-copilot",
        "level": level,
        "event_type": scenario_name,
        "agent_id": agent_id,
        "source_ip": src_ip,
        "service_name": "soc-copilot",
        "detected_level": level,
        "message": message,
        **details
    }

    return alert

def send_to_loki(alert: Dict, time_offset: int = 0) -> bool:
    """发送告警到 Loki"""
    try:
        # 构造 Loki payload
        labels = {
            "job": "soc-copilot",
            "level": alert["level"],
            "event_type": alert["event_type"],
            "agent_id": alert["agent_id"],
            "source_ip": alert["source_ip"],
            "service_name": "soc-copilot",
            "detected_level": alert["level"]
        }

        # 移除不能作为 label 的字段
        log_entry = {k: v for k, v in alert.items()
                    if k not in ["job", "level", "event_type", "agent_id", "source_ip", "service_name", "detected_level"]}

        payload = {
            "streams": [{
                "stream": labels,
                "values": [[get_timestamp_ns(time_offset), json.dumps(log_entry)]]
            }]
        }

        response = requests.post(LOKI_URL, json=payload, timeout=5)
        return response.status_code == 204

    except Exception as e:
        print(f"❌ 发送失败: {e}")
        return False

def generate_realistic_batch():
    """生成批量真实告警"""

    print("=" * 60)
    print("🚀 开始生成真实环境安全告警数据")
    print("=" * 60)

    print(f"\n📊 配置:")
    print(f"  • 总告警数量: {TOTAL_ALERTS}")
    print(f"  • 时间跨度: {TIME_SPAN_HOURS} 小时")
    print(f"  • 攻击场景: {len(ATTACK_SCENARIOS)} 种")
    print(f"  • 源 IP 地址: {len(SOURCE_IPS['internal'] + SOURCE_IPS['external'] + SOURCE_IPS['malicious'])} 个")
    print(f"  • Agent 数量: {len(AGENT_IDS)} 个")

    # 计算时间间隔
    time_span_seconds = TIME_SPAN_HOURS * 3600
    interval = time_span_seconds / TOTAL_ALERTS

    print(f"\n⏱️  时间分布:")
    print(f"  • 间隔: {interval:.2f} 秒")

    # 统计
    stats = {
        "total": 0,
        "by_level": {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0},
        "by_type": {},
        "by_source": {},
        "success": 0,
        "failed": 0
    }

    print(f"\n🔄 开始生成...")

    for i in range(TOTAL_ALERTS):
        # 计算时间偏移（从过去到现在）
        time_offset = int(time_span_seconds - (i * interval))

        # 生成告警
        alert = generate_alert(i + 1, time_offset)

        # 发送到 Loki
        if send_to_loki(alert, time_offset):
            stats["success"] += 1
        else:
            stats["failed"] += 1

        # 统计
        stats["total"] += 1
        level = alert["level"]
        stats["by_level"][level] = stats["by_level"].get(level, 0) + 1

        event_type = alert["event_type"]
        stats["by_type"][event_type] = stats["by_type"].get(event_type, 0) + 1

        src_ip = alert["source_ip"]
        stats["by_source"][src_ip] = stats["by_source"].get(src_ip, 0) + 1

        # 进度显示
        if (i + 1) % 50 == 0:
            print(f"  进度: {i + 1}/{TOTAL_ALERTS} ({((i + 1) / TOTAL_ALERTS * 100):.1f}%)")

        # 小延迟，避免过载
        time.sleep(0.01)

    print(f"\n✅ 生成完成!")
    print_statistics(stats)

    return stats

def print_statistics(stats: Dict):
    """打印统计信息"""
    print("\n" + "=" * 60)
    print("📊 统计信息")
    print("=" * 60)

    print(f"\n📈 总体统计:")
    print(f"  • 总告警数: {stats['total']}")
    print(f"  • 成功发送: {stats['success']}")
    print(f"  • 发送失败: {stats['failed']}")

    print(f"\n🎯 按严重级别分布:")
    for level, count in sorted(stats["by_level"].items(), key=lambda x: -x[1]):
        percentage = (count / stats["total"] * 100) if stats["total"] > 0 else 0
        bar = "█" * int(percentage / 2)
        emoji = {
            "critical": "🔴",
            "high": "🟠",
            "medium": "🟡",
            "low": "🟢",
            "info": "🔵"
        }.get(level, "⚪")
        print(f"  {emoji} {level.upper():10} {count:4} ({percentage:5.1f}%) {bar}")

    print(f"\n🔍 按攻击类型分布:")
    for attack_type, count in sorted(stats["by_type"].items(), key=lambda x: -x[1])[:10]:
        percentage = (count / stats["total"] * 100) if stats["total"] > 0 else 0
        print(f"  • {attack_type:20} {count:4} ({percentage:5.1f}%)")

    print(f"\n🌐 Top 10 攻击源 IP:")
    for ip, count in sorted(stats["by_source"].items(), key=lambda x: -x[1])[:10]:
        print(f"  • {ip:20} {count:4} 次攻击")

    print("\n" + "=" * 60)

if __name__ == "__main__":
    generate_realistic_batch()
