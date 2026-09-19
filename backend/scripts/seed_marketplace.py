"""Seed official community playbooks into marketplace_playbooks table.

Expands the marketplace with 24 realistic enterprise SOC playbooks across:
- Phishing & Email Security
- Ransomware & Endpoint Containment
- Malware & C2 Beacon Response
- Network Intrusion, DDoS & Cryptomining
- Identity, Pass-the-Hash & Insider Threat
- Data Exfiltration & Database Leakage
- Cloud Native & AWS/K8s Security
- Compliance & PCI-DSS/GDPR Auditing
"""

import json
import os
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import create_engine, text

PG_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://soc_sim_user:soc_sim_password_123456@127.0.0.1:15432/soc_sim_db",
)
SQLITE_URL = "sqlite:///data/app.db"

NOW = datetime.now(UTC)

OFFICIAL_PLAYBOOKS = [
    {
        "id": "market-pb-001",
        "name": "Phishing Email Auto-Response",
        "description": "针对钓鱼邮件告警的端到端自动化响应：提取发件人与恶意URL、查询威胁情报OTX、下发网关阻断并向受影响用户发送警示。",
        "version": "1.2.0",
        "category": "phishing",
        "difficulty": "beginner",
        "author_name": "SOC Copilot / NIST SP 800-61",
        "tags": [
            "standard:NIST SP 800-61",
            "att&ck:T1566.001",
            "att&ck:T1566.002",
            "phishing",
            "email",
            "ioc",
            "blocking",
            "otx"
        ],
        "verified": True,
        "featured": True,
        "download_count": 1250,
        "rating_average": 4.8,
        "rating_count": 45,
        "review_count": 12,
        "required_plugins": [
            "extract_iocs",
            "ti_lookup_otx",
            "http_request",
            "slack_notify"
        ],
        "compatible_versions": [
            "0.8.0",
            "0.9.0",
            "1.0.0"
        ],
        "dag_json": {
            "nodes": [
                {
                    "id": "start",
                    "type": "start",
                    "name": "Start"
                },
                {
                    "id": "extract_iocs",
                    "type": "extract_iocs",
                    "name": "Extract IOCs"
                },
                {
                    "id": "ti_lookup",
                    "type": "ti_lookup_otx",
                    "name": "Threat Intel Lookup"
                },
                {
                    "id": "block_iocs",
                    "type": "http_request",
                    "name": "Block Malicious IOCs"
                },
                {
                    "id": "notify_user",
                    "type": "slack_notify",
                    "name": "Notify User"
                },
                {
                    "id": "end",
                    "type": "end",
                    "name": "End"
                }
            ],
            "edges": [
                {
                    "source": "start",
                    "target": "extract_iocs"
                },
                {
                    "source": "extract_iocs",
                    "target": "ti_lookup"
                },
                {
                    "source": "ti_lookup",
                    "target": "block_iocs"
                },
                {
                    "source": "block_iocs",
                    "target": "notify_user"
                },
                {
                    "source": "notify_user",
                    "target": "end"
                }
            ]
        },
        "documentation": "# 🎣 Phishing Email Auto-Response (鱼叉钓鱼邮件自动化响应)\n\n## 📖 处置标准与依据\n- **国际权威标准**: [NIST SP 800-61 Rev.2](https://csrc.nist.gov/pubs/sp/800/61/r2/final) (计算机安全事件处置指南 Section 3.2: Detection & Analysis)\n- **攻防矩阵归属**: MITRE ATT&CK Enterprise Matrix\n- **剧本维护组织**: SOC Copilot 官方核心安全团队\n\n## 🛡️ MITRE ATT&CK 映射\n| 战术阶段 | 技术编号 | 技术名称 | 处置动作 |\n| :--- | :--- | :--- | :--- |\n| **Initial Access (初始访问)** | `T1566.001` | Spearphishing Attachment | 提取附件哈希并隔离 |\n| **Initial Access (初始访问)** | `T1566.002` | Spearphishing Link | 提取 URL 并下发网关黑名单 |\n| **Execution (执行)** | `T1204.001` | Malicious Link | 告警受影响用户并撤回邮件 |\n\n## 🎯 触发条件与适用范围\n- 邮件网关 (SEG) 检测到未通过 SPF/DKIM/DMARC 校验的高风险外发邮件；\n- 终端安全软件报出恶意链接点击重定向事件；\n- 企业员工通过 Outlook / Webmail 插件自主上报可疑鱼叉钓鱼告警。\n\n## 📋 标准应急响应处置流 (SOP)\n1. **取证与特征提取**:\n   - 自动解析原始 EML/MSG 报文，提取发送源 IP、真实发件人、邮件主题及所有内嵌超链接与附件；\n2. **多源情报富化 (Threat Intel Enrichment)**:\n   - 调用 AlienVault OTX、VirusTotal 查询发信 IP 与 URL 域名声誉及历史恶意家族标注；\n3. **网关阻断与全网遏制**:\n   - 联动边界防火墙与邮件安全网关下发黑名单规则；\n   - 检索全网邮箱，以 Message-ID 为索引批量撤回所有相同投递邮件；\n4. **受害者协同与补救**:\n   - 针对已点击链接的用户强制注销当前 Web Session 并重置密码；\n   - 自动发送安全教育警示提示用户防范高仿欺诈。"
    },
    {
        "id": "market-pb-009",
        "name": "Executive BEC Spear-Phishing Triage",
        "description": "针对高管仿冒与商务邮件欺诈（BEC）的高优先级研判剧本：识别相似高仿域名、核对发件人 SPF/DKIM/DMARC 认证并紧急通知财务冻结审批。",
        "version": "1.1.0",
        "category": "phishing",
        "difficulty": "intermediate",
        "author_name": "Cyber Defense Labs / MITRE ATT&CK",
        "tags": [
            "standard:MITRE ATT&CK",
            "att&ck:T1566",
            "att&ck:T1589",
            "bec",
            "phishing",
            "executive",
            "financial"
        ],
        "verified": True,
        "featured": False,
        "download_count": 870,
        "rating_average": 4.9,
        "rating_count": 31,
        "review_count": 8,
        "required_plugins": [
            "extract_iocs",
            "http_request",
            "slack_notify"
        ],
        "compatible_versions": [
            "0.8.0",
            "0.9.0",
            "1.0.0"
        ],
        "dag_json": {
            "nodes": [
                {
                    "id": "start",
                    "type": "start",
                    "name": "Start"
                },
                {
                    "id": "check_auth",
                    "type": "extract_iocs",
                    "name": "Inspect DMARC & Header"
                },
                {
                    "id": "typo_detect",
                    "type": "http_request",
                    "name": "Detect Lookalike Domain"
                },
                {
                    "id": "alert_finance",
                    "type": "slack_notify",
                    "name": "Freeze Financial Transfer"
                },
                {
                    "id": "end",
                    "type": "end",
                    "name": "End"
                }
            ],
            "edges": [
                {
                    "source": "start",
                    "target": "check_auth"
                },
                {
                    "source": "check_auth",
                    "target": "typo_detect"
                },
                {
                    "source": "typo_detect",
                    "target": "alert_finance"
                },
                {
                    "source": "alert_finance",
                    "target": "end"
                }
            ]
        },
        "documentation": "# 👔 Executive BEC Spear-Phishing Triage (高管商务邮件欺诈研判)\n\n## 📖 处置标准与依据\n- **国际权威标准**: [FBI IC3 BEC Advisory](https://www.ic3.gov/) & [MITRE ATT&CK T1566](https://attack.mitre.org/techniques/T1566/)\n- **合规指引**: 针对针对财务转账的高危假冒高管攻击（Business Email Compromise）\n\n## 🛡️ MITRE ATT&CK 映射\n- `T1566 (Phishing)`: 诱骗员工实施非受信业务操作\n- `T1589 (Gather Victim Identity Information)`: 攻击者收集内部高管职位与日程安排\n\n## 🎯 触发条件\n- 外部邮件发件人显示名称与企业内部 C-Level 高管姓名完全一致，但实际发信域为外部免费邮箱或相似域名；\n- 邮件正文中包含“加急转账”、“秘密收购”、“财务汇款审批”等高危敏感词汇。\n\n## 📋 标准处置流程 (SOP)\n1. **DMARC & 报头深度核验**: 检查邮件头原始 Received 链条，确认是否存在第三方中继或伪造；\n2. **相似李鬼域名识别**: 使用编辑距离算法比对发信域名与企业官方域名的字符差异；\n3. **财务流紧急阻断**: 自动向财务 ERP 系统下发拦截标记，暂时冻结 30 分钟内针对该账户的在途审批；\n4. **线下双人鉴权复核**: 触发语音电话或企业微信安全通道联系高管本人核实真实性。"
    },
    {
        "id": "market-pb-010",
        "name": "Malicious Attachment Detonation Pipeline",
        "description": "企业邮件网关拦截可疑未知附件后的自动化解包与多引擎杀毒处置：自动化沙箱静态分析、宏代码提取与全网隔离分发。",
        "version": "1.3.0",
        "category": "phishing",
        "difficulty": "intermediate",
        "author_name": "Palo Alto Cortex Community",
        "tags": [
            "standard:Cortex XSOAR",
            "att&ck:T1204.002",
            "att&ck:T1059",
            "attachment",
            "sandbox",
            "antivirus",
            "macro"
        ],
        "verified": True,
        "featured": False,
        "download_count": 1420,
        "rating_average": 4.7,
        "rating_count": 52,
        "review_count": 14,
        "required_plugins": [
            "extract_iocs",
            "ti_lookup_otx",
            "http_request"
        ],
        "compatible_versions": [
            "0.8.0",
            "0.9.0",
            "1.0.0"
        ],
        "dag_json": {
            "nodes": [
                {
                    "id": "start",
                    "type": "start",
                    "name": "Start"
                },
                {
                    "id": "extract_hash",
                    "type": "extract_iocs",
                    "name": "Extract Attachment SHA256"
                },
                {
                    "id": "virustotal",
                    "type": "ti_lookup_otx",
                    "name": "Query AV Multi-Engine"
                },
                {
                    "id": "quarantine",
                    "type": "http_request",
                    "name": "Quarantine Email in Gateway"
                },
                {
                    "id": "end",
                    "type": "end",
                    "name": "End"
                }
            ],
            "edges": [
                {
                    "source": "start",
                    "target": "extract_hash"
                },
                {
                    "source": "extract_hash",
                    "target": "virustotal"
                },
                {
                    "source": "virustotal",
                    "target": "quarantine"
                },
                {
                    "source": "quarantine",
                    "target": "end"
                }
            ]
        },
        "documentation": "# 💣 Malicious Attachment Detonation Pipeline (恶意附件自动化沙箱引爆)\n\n## 📖 处置标准与依据\n- **行业生态标准**: [Palo Alto Cortex XSOAR Playbook Reference](https://xsoar.pan.dev/)\n- **规范体系**: 遵循 CISA 恶意文件分析与处置流水线规范\n\n## 🛡️ MITRE ATT&CK 映射\n- `T1204.002 (Malicious File)`: 用户诱骗执行 Office 宏或嵌入式可执行载荷\n- `T1059 (Command and Scripting Interpreter)`: 宏代码拉起 PowerShell/CMD 执行下一阶段载荷\n\n## 📋 标准处置流程 (SOP)\n1. **附件提取与解包**: 自动剥离邮件中的未知 zip/rar/7z 压缩包及 Office 宏文档；\n2. **多引擎云端杀毒**: 调用主流杀毒引擎比对静态特征，计算 SHA256；\n3. **云沙箱动态引爆**: 自动化提交至沙箱，监控进程创建、注册表自启动项添加及可疑外联 IP；\n4. **全网邮件隔离**: 确认恶意后，秒级从邮件服务器邮箱中清除附件并全网分发告警。"
    },
    {
        "id": "market-pb-002",
        "name": "Ransomware Emergency Containment",
        "description": "勒索病毒感染活跃期的最高优先级处置剧本：网络秒级断网隔离、冻结高危凭据、快照取证并拉起专家应急工单。",
        "version": "2.0.0",
        "category": "ransomware",
        "difficulty": "advanced",
        "author_name": "SOC Copilot / NIST SP 800-61",
        "tags": [
            "standard:NIST SP 800-61",
            "att&ck:T1486",
            "att&ck:T1489",
            "ransomware",
            "emergency",
            "containment",
            "forensics",
            "edr"
        ],
        "verified": True,
        "featured": True,
        "download_count": 890,
        "rating_average": 4.9,
        "rating_count": 32,
        "review_count": 9,
        "required_plugins": [
            "isolate_host",
            "disable_account",
            "create_snapshot",
            "slack_notify"
        ],
        "compatible_versions": [
            "0.8.0",
            "0.9.0",
            "1.0.0"
        ],
        "dag_json": {
            "nodes": [
                {
                    "id": "start",
                    "type": "start",
                    "name": "Start"
                },
                {
                    "id": "isolate_host",
                    "type": "http_request",
                    "name": "Isolate Host Network"
                },
                {
                    "id": "disable_account",
                    "type": "http_request",
                    "name": "Disable Compromised Account"
                },
                {
                    "id": "snapshot",
                    "type": "http_request",
                    "name": "Create Forensic Snapshot"
                },
                {
                    "id": "notify",
                    "type": "slack_notify",
                    "name": "Alert Incident Commander"
                },
                {
                    "id": "end",
                    "type": "end",
                    "name": "End"
                }
            ],
            "edges": [
                {
                    "source": "start",
                    "target": "isolate_host"
                },
                {
                    "source": "isolate_host",
                    "target": "disable_account"
                },
                {
                    "source": "disable_account",
                    "target": "snapshot"
                },
                {
                    "source": "snapshot",
                    "target": "notify"
                },
                {
                    "source": "notify",
                    "target": "end"
                }
            ]
        },
        "documentation": "# 🚨 Ransomware Emergency Containment (勒索病毒应急遏制黄金5分钟)\n\n## 📖 处置标准与依据\n- **权威标准**: [NIST SP 800-61 Rev.2](https://csrc.nist.gov/pubs/sp/800/61/r2/final) (Section 3.3: Containment, Eradication, and Recovery)\n- **国家指引**: CISA & FBI #StopRansomware 指南\n\n## 🛡️ MITRE ATT&CK 映射\n- `T1486 (Data Encrypted for Impact)`: 攻击者批量加密本地与网络共享文件\n- `T1489 (Service Stop)`: 攻击者恶意停止数据库与核心关键服务\n- `T1490 (Inhibit System Recovery)`: 破坏系统恢复能力\n\n## 📋 标准应急响应处置流 (SOP)\n1. **网络秒级断开 (Host Isolation)**:\n   - 立即通过 EDR 下发单机网络隔离策略，仅保留管理心跳端口，阻断内网横向加密；\n2. **凭据冻结 (Credential Revocation)**:\n   - 自动禁用该主机最近登录的所有 AD 域账号与本地管理员会话；\n3. **内存与磁盘保全 (Forensic Snapshot)**:\n   - 触发虚拟化底座或物理盘只读快照，保全被加密前的内存镜像与关键事件日志；\n4. **激活紧急应急指挥部**:\n   - 自动在通信群组（Slack/钉钉/企业微信）拉起指挥通道，向 CISO 和安全值班负责人广播。"
    },
    {
        "id": "market-pb-011",
        "name": "Shadow Copy & VSS Tampering Defense",
        "description": "检测攻击者通过 vssadmin/WMI 删除 Windows 卷影副本的特征指令：自动熔断本地特权进程、上报防御事件并触发异地冷备只读锁定。",
        "version": "1.0.0",
        "category": "ransomware",
        "difficulty": "advanced",
        "author_name": "SANS DFIR Guild",
        "tags": [
            "standard:MITRE ATT&CK",
            "att&ck:T1490",
            "vss",
            "shadow_copy",
            "ransomware",
            "backup",
            "edr"
        ],
        "verified": True,
        "featured": False,
        "download_count": 760,
        "rating_average": 4.8,
        "rating_count": 28,
        "review_count": 6,
        "required_plugins": [
            "http_request",
            "slack_notify"
        ],
        "compatible_versions": [
            "0.8.0",
            "0.9.0",
            "1.0.0"
        ],
        "dag_json": {
            "nodes": [
                {
                    "id": "start",
                    "type": "start",
                    "name": "Start"
                },
                {
                    "id": "kill_proc",
                    "type": "http_request",
                    "name": "Kill Malicious VSS Process"
                },
                {
                    "id": "lock_backup",
                    "type": "http_request",
                    "name": "Lock Immutable NAS Storage"
                },
                {
                    "id": "alert",
                    "type": "slack_notify",
                    "name": "Broadcast Ransomware Pre-cursor Alert"
                },
                {
                    "id": "end",
                    "type": "end",
                    "name": "End"
                }
            ],
            "edges": [
                {
                    "source": "start",
                    "target": "kill_proc"
                },
                {
                    "source": "kill_proc",
                    "target": "lock_backup"
                },
                {
                    "source": "lock_backup",
                    "target": "alert"
                },
                {
                    "source": "alert",
                    "target": "end"
                }
            ]
        },
        "documentation": "# 🛡️ Shadow Copy & VSS Tampering Defense (卷影副本防篡改防御)\n\n## 📖 处置标准与依据\n- **国际权威标准**: [MITRE ATT&CK T1490](https://attack.mitre.org/techniques/T1490/) (Inhibit System Recovery)\n- **实战指南**: SANS DFIR 勒索软件阻断对抗实录\n\n## 🎯 典型攻击特征\n- 攻击者通过 `vssadmin delete shadows /all /quiet` 或 `wmic shadowcopy delete` 企图剥夺受害者的自愈还原能力。\n\n## 📋 标准处置流程 (SOP)\n1. **特权进程瞬时阻断**: EDR 拦截到调用卷影删除指令的瞬间，直接强杀发起进程；\n2. **异地不可篡改冷备锁定**: 联动企业存储集群（WORM 存储 / NAS），进入只读保护状态；\n3. **提升严重等级**: 将告警等级提升至 P0（Critical Pre-cursor），通报应急响应专家进场排查。"
    },
    {
        "id": "market-pb-012",
        "name": "Ransomware Decryption & System Restoration",
        "description": "勒索处置后的受害系统恢复工作流：匹配 NoMoreRansom 开源解密密钥库、验证文件完整性并自动从干净时间点执行还原编排。",
        "version": "1.2.0",
        "category": "ransomware",
        "difficulty": "intermediate",
        "author_name": "Europol NoMoreRansom Project",
        "tags": [
            "standard:ISO 27035",
            "att&ck:T1486",
            "ransomware",
            "restoration",
            "decryption",
            "backup"
        ],
        "verified": False,
        "featured": False,
        "download_count": 630,
        "rating_average": 4.6,
        "rating_count": 19,
        "review_count": 4,
        "required_plugins": [
            "http_request",
            "human_approval",
            "generate_report"
        ],
        "compatible_versions": [
            "0.8.0",
            "0.9.0",
            "1.0.0"
        ],
        "dag_json": {
            "nodes": [
                {
                    "id": "start",
                    "type": "start",
                    "name": "Start"
                },
                {
                    "id": "match_key",
                    "type": "http_request",
                    "name": "Query Known Decryption DB"
                },
                {
                    "id": "approval",
                    "type": "human_approval",
                    "name": "Confirm Clean Restore Snapshot"
                },
                {
                    "id": "rebuild",
                    "type": "http_request",
                    "name": "Execute Orchestrated VM Restore"
                },
                {
                    "id": "end",
                    "type": "end",
                    "name": "End"
                }
            ],
            "edges": [
                {
                    "source": "start",
                    "target": "match_key"
                },
                {
                    "source": "match_key",
                    "target": "approval"
                },
                {
                    "source": "approval",
                    "target": "rebuild"
                },
                {
                    "source": "rebuild",
                    "target": "end"
                }
            ]
        },
        "documentation": "# 🔑 Ransomware Decryption & System Restoration (勒索灾后恢复与密钥匹配)\n\n## 📖 处置标准与依据\n- **开源标准倡议**: [NoMoreRansom.org](https://www.nomoreransom.org/)\n- **合规标准**: [ISO/IEC 27035](https://www.iso.org/standard/60803.html) 信息安全事件管理与灾难恢复规范\n\n## 📋 标准处置流程 (SOP)\n1. **勒索家族识别**: 读取勒索信特征及被加密文件后缀，比对全球已知勒索变种；\n2. **解密工具检索**: 自动化检索 NoMoreRansom 开源公私钥库，尝试解密样本验证成功率；\n3. **干净还原点人工审批**: 列出被感染前最近一份可信快照，由基础设施团队双人审批签字；\n4. **编排还原执行**: 自动化下发还原镜像，并进行代码和系统安全基线扫描后重新入网。"
    },
    {
        "id": "market-pb-003",
        "name": "Malware Analysis & Quarantine",
        "description": "终端端点检测到未知可疑样本后的自动化沙箱分析与处置链路：调用沙箱动态分析行为、研判恶意程度并同步下发 EDR 隔离。",
        "version": "1.5.0",
        "category": "malware_response",
        "difficulty": "intermediate",
        "author_name": "SOC Copilot / NIST SP 800-61",
        "tags": [
            "standard:NIST SP 800-61",
            "att&ck:T1204",
            "att&ck:T1059",
            "malware",
            "sandbox",
            "quarantine",
            "edr"
        ],
        "verified": True,
        "featured": True,
        "download_count": 2100,
        "rating_average": 4.7,
        "rating_count": 89,
        "review_count": 21,
        "required_plugins": [
            "extract_iocs",
            "ti_lookup_otx",
            "http_request"
        ],
        "compatible_versions": [
            "0.8.0",
            "0.9.0",
            "1.0.0"
        ],
        "dag_json": {
            "nodes": [
                {
                    "id": "start",
                    "type": "start",
                    "name": "Start"
                },
                {
                    "id": "extract",
                    "type": "extract_iocs",
                    "name": "Extract Sample Hash"
                },
                {
                    "id": "ti",
                    "type": "ti_lookup_otx",
                    "name": "Query Threat Feeds"
                },
                {
                    "id": "quarantine",
                    "type": "http_request",
                    "name": "Quarantine Malicious Binary"
                },
                {
                    "id": "end",
                    "type": "end",
                    "name": "End"
                }
            ],
            "edges": [
                {
                    "source": "start",
                    "target": "extract"
                },
                {
                    "source": "extract",
                    "target": "ti"
                },
                {
                    "source": "ti",
                    "target": "quarantine"
                },
                {
                    "source": "quarantine",
                    "target": "end"
                }
            ]
        },
        "documentation": "# 🦠 Malware Analysis & Quarantine (恶意代码自动化研判与隔离)\n\n## 📖 处置标准与依据\n- **国际权威标准**: [NIST SP 800-61 Rev.2](https://csrc.nist.gov/pubs/sp/800/61/r2/final)\n- **攻防标准**: MITRE ATT&CK Enterprise Matrix\n\n## 🛡️ MITRE ATT&CK 映射\n- `T1204 (User Execution)`: 恶意代码被执行\n- `T1059 (Command and Scripting Interpreter)`: 脚本与命令行执行\n\n## 📋 标准处置流程 (SOP)\n1. **端点样本抓取**: 从端点提取可疑样本文件及启动项参数；\n2. **威胁情报查询**: 查询各大公私情报库计算哈希信誉分；\n3. **端点处置落地**: 判定恶意后，EDR 自动粉碎目标文件，回滚注册表改动；\n4. **全网免疫防护**: 自动生成 Yara / IOC 规则推送到全网所有防护探针。"
    },
    {
        "id": "market-pb-013",
        "name": "Cobalt Strike Beacon C2 Triage",
        "description": "检测内网终端周期性心跳可疑外联（Cobalt Strike / Sliver / Metasploit C2）：提取证书特征、JA3指纹，防火墙自动阻断外部域名并下发内存转储。",
        "version": "2.1.0",
        "category": "malware_response",
        "difficulty": "advanced",
        "author_name": "Splunk SOAR Community",
        "tags": [
            "standard:MITRE ATT&CK",
            "att&ck:T1071.001",
            "att&ck:T1573",
            "cobalt_strike",
            "c2",
            "beacon",
            "ja3"
        ],
        "verified": True,
        "featured": True,
        "download_count": 3200,
        "rating_average": 4.9,
        "rating_count": 115,
        "review_count": 34,
        "required_plugins": [
            "extract_iocs",
            "ti_lookup_otx",
            "http_request",
            "slack_notify"
        ],
        "compatible_versions": [
            "0.8.0",
            "0.9.0",
            "1.0.0"
        ],
        "dag_json": {
            "nodes": [
                {
                    "id": "start",
                    "type": "start",
                    "name": "Start"
                },
                {
                    "id": "parse_c2",
                    "type": "extract_iocs",
                    "name": "Analyze Jitter & Heartbeat"
                },
                {
                    "id": "dns_sinkhole",
                    "type": "http_request",
                    "name": "DNS Sinkhole C2 Domain"
                },
                {
                    "id": "mem_dump",
                    "type": "http_request",
                    "name": "Trigger EDR Memory Dump"
                },
                {
                    "id": "alert",
                    "type": "slack_notify",
                    "name": "Escalate Critical Active C2"
                },
                {
                    "id": "end",
                    "type": "end",
                    "name": "End"
                }
            ],
            "edges": [
                {
                    "source": "start",
                    "target": "parse_c2"
                },
                {
                    "source": "parse_c2",
                    "target": "dns_sinkhole"
                },
                {
                    "source": "dns_sinkhole",
                    "target": "mem_dump"
                },
                {
                    "source": "mem_dump",
                    "target": "alert"
                },
                {
                    "source": "alert",
                    "target": "end"
                }
            ]
        },
        "documentation": "# 📡 Cobalt Strike Beacon C2 Triage (C2 远控信标研判与阻断)\n\n## 📖 处置标准与依据\n- **行业剧本标准**: [Splunk SOAR Community Playbooks](https://research.splunk.com/)\n- **攻防标准**: MITRE ATT&CK T1071.001 (Application Layer Protocol: Web Protocols)\n\n## 🛡️ MITRE ATT&CK 映射\n- `T1071.001 (Web Protocols)`: 使用 HTTP/HTTPS 伪装为正常业务流量与远控服务端通信\n- `T1573 (Encrypted Channel)`: 双向非对称加密传输指令\n\n## 📋 标准处置流程 (SOP)\n1. **流量抖动与周期性分析**: 深度解析通信包间隔与 Jitter 规律，提取 JA3 TLS 指纹；\n2. **DNS 沉洞拦截**: 边界 DNS 服务器将 C2 域名指向内网安全沉洞（Sinkhole）抓取受害者 IP；\n3. **内存转储取证**: 触发受害终端 EDR 提取关键进程内存 Dump 留存；\n4. **阻断升级**: 防火墙秒级封禁远程服务端 IP 端口。"
    },
    {
        "id": "market-pb-014",
        "name": "WebShell & Memory Horse Backdoor Purge",
        "description": "针对 Web 服务器告警上传/写入木马脚本事件：快速比对文件哈希、定位受害应用进程、杀除 Java 内存马注入线程并恢复代码基线。",
        "version": "1.4.0",
        "category": "malware_response",
        "difficulty": "intermediate",
        "author_name": "Application Security Guild / OWASP",
        "tags": [
            "standard:OWASP Top 10",
            "att&ck:T1505.003",
            "webshell",
            "memory_horse",
            "backdoor",
            "waf",
            "java"
        ],
        "verified": True,
        "featured": False,
        "download_count": 1890,
        "rating_average": 4.8,
        "rating_count": 76,
        "review_count": 18,
        "required_plugins": [
            "http_request",
            "slack_notify"
        ],
        "compatible_versions": [
            "0.8.0",
            "0.9.0",
            "1.0.0"
        ],
        "dag_json": {
            "nodes": [
                {
                    "id": "start",
                    "type": "start",
                    "name": "Start"
                },
                {
                    "id": "find_file",
                    "type": "http_request",
                    "name": "Verify Web File Hash Baseline"
                },
                {
                    "id": "isolate_app",
                    "type": "http_request",
                    "name": "Remove Server from Load Balancer"
                },
                {
                    "id": "delete_shell",
                    "type": "http_request",
                    "name": "Purge File & Detach Memory Agent"
                },
                {
                    "id": "end",
                    "type": "end",
                    "name": "End"
                }
            ],
            "edges": [
                {
                    "source": "start",
                    "target": "find_file"
                },
                {
                    "source": "find_file",
                    "target": "isolate_app"
                },
                {
                    "source": "isolate_app",
                    "target": "delete_shell"
                },
                {
                    "source": "delete_shell",
                    "target": "end"
                }
            ]
        },
        "documentation": "# 🗡️ WebShell & Memory Horse Backdoor Purge (后门与内存马彻底清除)\n\n## 📖 处置标准与依据\n- **行业权威规范**: [OWASP Top 10 A03:2021 Injection](https://owasp.org/Top10/)\n- **攻防技术**: MITRE ATT&CK `T1505.003` (Server Software Component: Web Shell)\n\n## 📋 标准处置流程 (SOP)\n1. **静态基线哈希比对**: 快速遍历 Web 根目录，比对 Git 纯净版本库排查新增与篡改脚本；\n2. **负载均衡摘除**: 将被入侵的业务服务器从集群 Load Balancer 中摘除，避免脏流量继续处理；\n3. **内存马排查与卸载**: 排查 Java Filter/Servlet/Listener 动态注入项，调用 Agent 卸载恶意字节码；\n4. **重置部署**: 清除后门后重新从 CI/CD 干净构建制品重新发布。"
    },
    {
        "id": "market-pb-006",
        "name": "Brute Force Defense & Dynamic Blacklist",
        "description": "针对 SSH/RDP/Web 登录高频爆破事件，自动提取源 IP 与攻击特征，动态在边缘边界防火墙加入黑名单封禁并进行资产排查。",
        "version": "1.1.0",
        "category": "network_intrusion",
        "difficulty": "beginner",
        "author_name": "SOC Copilot / MITRE ATT&CK",
        "tags": [
            "standard:MITRE ATT&CK",
            "att&ck:T1110",
            "bruteforce",
            "ssh",
            "rdp",
            "firewall",
            "ip_ban"
        ],
        "verified": True,
        "featured": True,
        "download_count": 1680,
        "rating_average": 4.8,
        "rating_count": 64,
        "review_count": 15,
        "required_plugins": [
            "extract_iocs",
            "http_request",
            "slack_notify"
        ],
        "compatible_versions": [
            "0.8.0",
            "0.9.0",
            "1.0.0"
        ],
        "dag_json": {
            "nodes": [
                {
                    "id": "start",
                    "type": "start",
                    "name": "Start"
                },
                {
                    "id": "extract_ip",
                    "type": "extract_iocs",
                    "name": "Extract Attacker IP"
                },
                {
                    "id": "ban_ip",
                    "type": "http_request",
                    "name": "Add Firewall Blacklist"
                },
                {
                    "id": "notify",
                    "type": "slack_notify",
                    "name": "Notify On-call"
                },
                {
                    "id": "end",
                    "type": "end",
                    "name": "End"
                }
            ],
            "edges": [
                {
                    "source": "start",
                    "target": "extract_ip"
                },
                {
                    "source": "extract_ip",
                    "target": "ban_ip"
                },
                {
                    "source": "ban_ip",
                    "target": "notify"
                },
                {
                    "source": "notify",
                    "target": "end"
                }
            ]
        },
        "documentation": "# 🔨 Brute Force Defense & Dynamic Blacklist (暴力破解动态封禁)\n\n## 📖 处置标准与依据\n- **国际权威规范**: [MITRE ATT&CK T1110](https://attack.mitre.org/techniques/T1110/) (Brute Force)\n- **处置指引**: NIST SP 800-61 Section 3.2: Automated Network Containment\n\n## 📋 标准处置流程 (SOP)\n1. **爆破特征提取**: 聚合统计单位时间内来自同一源 IP 对 SSH/RDP/Web 接口的失败次数；\n2. **动态黑名单下发**: 超过阈值后自动调用边缘防火墙 / API 网关封禁攻击源 24 小时；\n3. **成功登录校验**: 排查同一 IP 是否存在一次“登录成功”记录，若存在则立即冻结该账号并强制踢下线；\n4. **事件闭单与通报**: 记录工单并向运维安全组通报高风险账号。"
    },
    {
        "id": "market-pb-015",
        "name": "High-Volume DDoS Mitigation & WAF Sync",
        "description": "监测入站流量突增与 SYN Flood / HTTP Flood 攻击：自动拉高 Cloudflare / AWS Shield 清洗防护阈值，并将恶意源网段同步下发防篡改保护。",
        "version": "2.0.0",
        "category": "network_intrusion",
        "difficulty": "intermediate",
        "author_name": "Cloudflare Defense Guidelines",
        "tags": [
            "standard:NIST SP 800-61",
            "att&ck:T1498",
            "ddos",
            "waf",
            "scrubbing",
            "rate_limit"
        ],
        "verified": True,
        "featured": False,
        "download_count": 1150,
        "rating_average": 4.7,
        "rating_count": 43,
        "review_count": 11,
        "required_plugins": [
            "http_request",
            "slack_notify"
        ],
        "compatible_versions": [
            "0.8.0",
            "0.9.0",
            "1.0.0"
        ],
        "dag_json": {
            "nodes": [
                {
                    "id": "start",
                    "type": "start",
                    "name": "Start"
                },
                {
                    "id": "eval_traffic",
                    "type": "http_request",
                    "name": "Evaluate Flow Threshold"
                },
                {
                    "id": "waf_challenge",
                    "type": "http_request",
                    "name": "Activate Under Attack Challenge"
                },
                {
                    "id": "notify_noc",
                    "type": "slack_notify",
                    "name": "Page NOC & Infrastructure Lead"
                },
                {
                    "id": "end",
                    "type": "end",
                    "name": "End"
                }
            ],
            "edges": [
                {
                    "source": "start",
                    "target": "eval_traffic"
                },
                {
                    "source": "eval_traffic",
                    "target": "waf_challenge"
                },
                {
                    "source": "waf_challenge",
                    "target": "notify_noc"
                },
                {
                    "source": "notify_noc",
                    "target": "end"
                }
            ]
        },
        "documentation": "# 🌊 High-Volume DDoS Mitigation & WAF Sync (大流量 DDoS 缓解清洗)\n\n## 📖 处置标准与依据\n- **网络防御架构**: Cloudflare Anycast DDoS Mitigation Guidelines\n- **应急标准**: NIST SP 800-61 Rev.2\n\n## 🛡️ MITRE ATT&CK 映射\n- `T1498 (Network Denial of Service)`: 制造网络服务不可用\n\n## 📋 标准处置流程 (SOP)\n1. **异常流量激增告警**: 监控边界入向带宽与 SYN/UDP 包比率激增事件；\n2. **一键切换云端高防清洗**: 自动更新 BGP 宣告，将流量牵引至云清洗中心过滤脏流量；\n3. **WAF 启用交互挑战**: 开启针对应用层 HTTP Flood 的 JS Challenge 与验证码机制；\n4. **源站保护校验**: 确保护盾源站仅响应清洗中心回源 IP，拦截直接针对源站的嗅探。"
    },
    {
        "id": "market-pb-016",
        "name": "Cryptomining Pool Traffic Cutoff",
        "description": "联动全网流量分析发现内网挖矿木马（XMRig / Stratum协议）外联特征：快速提取目标矿池域名与钱包地址，在 DNS 与核心路由截断通信并定位内网感染源机器。",
        "version": "1.3.0",
        "category": "network_intrusion",
        "difficulty": "beginner",
        "author_name": "Cloud Threat Research / MITRE ATT&CK",
        "tags": [
            "standard:MITRE ATT&CK",
            "att&ck:T1496",
            "cryptomining",
            "stratum",
            "firewall",
            "edr"
        ],
        "verified": True,
        "featured": True,
        "download_count": 2450,
        "rating_average": 4.9,
        "rating_count": 94,
        "review_count": 27,
        "required_plugins": [
            "extract_iocs",
            "http_request",
            "slack_notify"
        ],
        "compatible_versions": [
            "0.8.0",
            "0.9.0",
            "1.0.0"
        ],
        "dag_json": {
            "nodes": [
                {
                    "id": "start",
                    "type": "start",
                    "name": "Start"
                },
                {
                    "id": "parse_stratum",
                    "type": "extract_iocs",
                    "name": "Extract Mining Pool Domain"
                },
                {
                    "id": "sinkhole",
                    "type": "http_request",
                    "name": "DNS Sinkhole Mining Domain"
                },
                {
                    "id": "kill_miner",
                    "type": "http_request",
                    "name": "Send Terminate Command to Agent"
                },
                {
                    "id": "end",
                    "type": "end",
                    "name": "End"
                }
            ],
            "edges": [
                {
                    "source": "start",
                    "target": "parse_stratum"
                },
                {
                    "source": "parse_stratum",
                    "target": "sinkhole"
                },
                {
                    "source": "sinkhole",
                    "target": "kill_miner"
                },
                {
                    "source": "kill_miner",
                    "target": "end"
                }
            ]
        },
        "documentation": "# ⛏️ Cryptomining Pool Traffic Cutoff (挖矿木马全链路切断)\n\n## 📖 处置标准与依据\n- **攻防标准**: [MITRE ATT&CK T1496](https://attack.mitre.org/techniques/T1496/) (Resource Hijacking)\n- **安全指引**: CISA 关于企业云主机非法算力占用的防御建议\n\n## 📋 标准处置流程 (SOP)\n1. **矿池连接识别**: 捕获主机向外部未知端口发起 Stratum/JSON-RPC 协议流量；\n2. **网络边缘拦截**: 边界防火墙秒级封禁远程矿池 IP 与常用挖矿域名；\n3. **恶意进程清理**: 识别高 CPU 占用的恶意进程，清理定时任务 crontab 与 systemd 服务单元；\n4. **溯源入口加固**: 排查弱口令、Redis 未授权访问或未修补的 RCE 漏洞。"
    },
    {
        "id": "market-pb-017",
        "name": "SQL Injection & API Parameter Exploit Block",
        "description": "Web API 接口遭受盲注、联合查询与报错注入攻击时的实时拦截策略：联动 WAF 对攻击源 IP 实施临时访问拉黑，并将 payload 提交至研发安全漏洞库。",
        "version": "1.1.0",
        "category": "network_intrusion",
        "difficulty": "intermediate",
        "author_name": "OWASP Foundation Standard",
        "tags": [
            "standard:OWASP Top 10",
            "att&ck:T1190",
            "sqli",
            "injection",
            "waf",
            "database"
        ],
        "verified": False,
        "featured": False,
        "download_count": 1340,
        "rating_average": 4.6,
        "rating_count": 48,
        "review_count": 10,
        "required_plugins": [
            "extract_iocs",
            "http_request"
        ],
        "compatible_versions": [
            "0.8.0",
            "0.9.0",
            "1.0.0"
        ],
        "dag_json": {
            "nodes": [
                {
                    "id": "start",
                    "type": "start",
                    "name": "Start"
                },
                {
                    "id": "extract_param",
                    "type": "extract_iocs",
                    "name": "Extract SQLi Payload"
                },
                {
                    "id": "block_ip",
                    "type": "http_request",
                    "name": "Apply WAF Temporary Rate Limit"
                },
                {
                    "id": "create_ticket",
                    "type": "http_request",
                    "name": "File AppSec Remediation Ticket"
                },
                {
                    "id": "end",
                    "type": "end",
                    "name": "End"
                }
            ],
            "edges": [
                {
                    "source": "start",
                    "target": "extract_param"
                },
                {
                    "source": "extract_param",
                    "target": "block_ip"
                },
                {
                    "source": "block_ip",
                    "target": "create_ticket"
                },
                {
                    "source": "create_ticket",
                    "target": "end"
                }
            ]
        },
        "documentation": "# 💉 SQL Injection & API Parameter Exploit Block (SQL 注入阻断)\n\n## 📖 处置标准与依据\n- **国际应用安全权威**: [OWASP Top 10 A03:2021-Injection](https://owasp.org/Top10/)\n- **合规映射**: PCI-DSS Requirement 6.4 (Protect Web Applications)\n\n## 🛡️ MITRE ATT&CK 映射\n- `T1190 (Exploit Public-Facing Application)`: 利用公开 Web 应用漏洞\n\n## 📋 标准处置流程 (SOP)\n1. **注入 Payload 捕获**: WAF 侦测到 URL/Body 中包含布尔盲注、联合查询或延时注入特征；\n2. **IP 动态惩罚与封禁**: 阻断当前请求并将攻击者 IP 列入 WAF 临时封禁池；\n3. **数据泄露核验**: 检索数据库审计系统，确认该注入语句是否实际返回敏感数据表数据；\n4. **研发协同修复**: 自动导出该接口的详细请求复现数据并指派修复工单。"
    },
    {
        "id": "market-pb-005",
        "name": "Insider Threat & UEBA Anomaly Hunting",
        "description": "结合用户与实体行为分析（UEBA）基线偏移的深度研判剧本：关联非工作时间高频越权访问、异地漫游登录，综合研判风险分。",
        "version": "1.0.0",
        "category": "insider_threat",
        "difficulty": "advanced",
        "author_name": "SOC Copilot / CERT Insider Threat Center",
        "tags": [
            "standard:CISA",
            "att&ck:T1078",
            "att&ck:T1005",
            "insider_threat",
            "ueba",
            "anomaly",
            "dlp"
        ],
        "verified": True,
        "featured": False,
        "download_count": 432,
        "rating_average": 4.4,
        "rating_count": 18,
        "review_count": 5,
        "required_plugins": [
            "http_request",
            "human_approval",
            "slack_notify"
        ],
        "compatible_versions": [
            "0.8.0",
            "0.9.0",
            "1.0.0"
        ],
        "dag_json": {
            "nodes": [
                {
                    "id": "start",
                    "type": "start",
                    "name": "Start"
                },
                {
                    "id": "eval_risk",
                    "type": "http_request",
                    "name": "Evaluate UEBA Baseline"
                },
                {
                    "id": "approval",
                    "type": "human_approval",
                    "name": "Manager Escalation Review"
                },
                {
                    "id": "notify",
                    "type": "slack_notify",
                    "name": "Notify SecOps"
                },
                {
                    "id": "end",
                    "type": "end",
                    "name": "End"
                }
            ],
            "edges": [
                {
                    "source": "start",
                    "target": "eval_risk"
                },
                {
                    "source": "eval_risk",
                    "target": "approval"
                },
                {
                    "source": "approval",
                    "target": "notify"
                },
                {
                    "source": "notify",
                    "target": "end"
                }
            ]
        },
        "documentation": "# 🕵️ Insider Threat & UEBA Anomaly Hunting (内部威胁与异常行为排查)\n\n## 📖 处置标准与依据\n- **权威指引**: [CISA Insider Threat Mitigation Guide](https://www.cisa.gov/)\n- **研究模型**: CMU CERT Insider Threat Center Architecture\n\n## 🛡️ MITRE ATT&CK 映射\n- `T1078 (Valid Accounts)`: 内部员工利用已授权合法账号执行越权操作\n- `T1005 (Data from Local System)`: 批量提取本地或网络驱动器资料\n\n## 📋 标准处置流程 (SOP)\n1. **UEBA 行为偏离告警**: 捕获员工非正常工作时段的大量下载、异常外发等异常偏离基线事件；\n2. **敏感权限动态收敛**: 临时降低该员工访问核心机密数据库的权限等级；\n3. **DLP 证据链存证**: 自动归档终端操作录屏、网络流量日志及 USB 外发操作记录；\n4. **合规审查通知**: 按照企业人事安全流程，向安全委员会与法务主管提报审批。"
    },
    {
        "id": "market-pb-018",
        "name": "Pass-the-Hash & Kerberoasting Lateral Defense",
        "description": "监测内网 Active Directory 域控中可疑 Kerberos 服务票据申请与哈希传递凭证横向移动：自动使失陷 Kerberos 票据失效并重置 krbtgt 密钥。",
        "version": "2.0.0",
        "category": "insider_threat",
        "difficulty": "advanced",
        "author_name": "Active Directory Security Working Group",
        "tags": [
            "standard:MITRE ATT&CK",
            "att&ck:T1550.002",
            "att&ck:T1558.003",
            "active_directory",
            "kerberoasting",
            "pass_the_hash",
            "lateral_movement"
        ],
        "verified": True,
        "featured": True,
        "download_count": 980,
        "rating_average": 4.8,
        "rating_count": 39,
        "review_count": 11,
        "required_plugins": [
            "http_request",
            "slack_notify"
        ],
        "compatible_versions": [
            "0.8.0",
            "0.9.0",
            "1.0.0"
        ],
        "dag_json": {
            "nodes": [
                {
                    "id": "start",
                    "type": "start",
                    "name": "Start"
                },
                {
                    "id": "detect_spn",
                    "type": "http_request",
                    "name": "Verify Unusual SPN Request"
                },
                {
                    "id": "revoke_ticket",
                    "type": "http_request",
                    "name": "Revoke User TGT Ticket"
                },
                {
                    "id": "alert_ad",
                    "type": "slack_notify",
                    "name": "Escalate Domain Controller Event"
                },
                {
                    "id": "end",
                    "type": "end",
                    "name": "End"
                }
            ],
            "edges": [
                {
                    "source": "start",
                    "target": "detect_spn"
                },
                {
                    "source": "detect_spn",
                    "target": "revoke_ticket"
                },
                {
                    "source": "revoke_ticket",
                    "target": "alert_ad"
                },
                {
                    "source": "alert_ad",
                    "target": "end"
                }
            ]
        },
        "documentation": "# 🎫 Pass-the-Hash & Kerberoasting Lateral Defense (哈希传递与黄金票据防御)\n\n## 📖 处置标准与依据\n- **国际攻防标准**: [MITRE ATT&CK T1550.002](https://attack.mitre.org/techniques/T1550/002/) & [T1558.003](https://attack.mitre.org/techniques/T1558/003/)\n- **合规指引**: Microsoft Security Baselines for Active Directory\n\n## 📋 标准处置流程 (SOP)\n1. **域控审计捕获**: 监控 Windows Event ID 4769、4776，侦测 Kerberos 票据请求异常暴增；\n2. **账号密码重置与吊销**: 强制重置受害服务账号密码，失效已签发的 Kerberos TGT 票据；\n3. **主机 RPC 隔离**: 切断受控主机对内网其他资产的 445/135 端口访问；\n4. **特权组审计**: 审查 Domain Admins、Enterprise Admins 特权组成员变动情况。"
    },
    {
        "id": "market-pb-019",
        "name": "Off-Hours Mass Data Download by Service Account",
        "description": "监控业务服务账号（Service Account）在非工作时间批量导出敏感数据表记录：自动限制该 Token 访问权限，阻断并发并调取调用方 IP 上下文。",
        "version": "1.1.0",
        "category": "insider_threat",
        "difficulty": "intermediate",
        "author_name": "Zero Trust Identity Defense Group",
        "tags": [
            "standard:CIS",
            "att&ck:T1078.002",
            "att&ck:T1530",
            "service_account",
            "off_hours",
            "data_download",
            "zero_trust"
        ],
        "verified": False,
        "featured": False,
        "download_count": 520,
        "rating_average": 4.5,
        "rating_count": 22,
        "review_count": 5,
        "required_plugins": [
            "http_request",
            "slack_notify"
        ],
        "compatible_versions": [
            "0.8.0",
            "0.9.0",
            "1.0.0"
        ],
        "dag_json": {
            "nodes": [
                {
                    "id": "start",
                    "type": "start",
                    "name": "Start"
                },
                {
                    "id": "throttle_token",
                    "type": "http_request",
                    "name": "Rate-Limit Service Token"
                },
                {
                    "id": "verify_owner",
                    "type": "slack_notify",
                    "name": "Ping Service Account Owner"
                },
                {
                    "id": "end",
                    "type": "end",
                    "name": "End"
                }
            ],
            "edges": [
                {
                    "source": "start",
                    "target": "throttle_token"
                },
                {
                    "source": "throttle_token",
                    "target": "verify_owner"
                },
                {
                    "source": "verify_owner",
                    "target": "end"
                }
            ]
        },
        "documentation": "# 🌙 Off-Hours Mass Data Download by Service Account (非工作时间服务账号批量下载)\n\n## 📖 处置标准与依据\n- **行业权威规范**: [CIS Controls v8 Safeguard 6.3](https://www.cisecurity.org/)\n- **架构准则**: NIST SP 800-207 Zero Trust Architecture (持续凭据认证)\n\n## 📋 标准处置流程 (SOP)\n1. **行为基线比对**: 比对自动化服务账号历史调用频次及时间窗口分布；\n2. **API 令牌应急撤回**: 自动吊销当前活跃的 OAuth 访问凭据与临时 STS Token；\n3. **外联 IP 定位**: 检查调用源 IP 是否来自未知公网环境，阻断非法网段访问；\n4. **责任人双因素确认**: 触发钉钉/企业微信机器人通知该接口负责人确认是否为合规批量任务。"
    },
    {
        "id": "market-pb-004",
        "name": "Data Exfiltration Investigation",
        "description": "针对海量异常外联或跨境大流量的数据外发排查剧本：联动网络日志、定位异常访问的文件与脱敏资产、计算数据影响面评估。",
        "version": "1.0.0",
        "category": "data_breach",
        "difficulty": "intermediate",
        "author_name": "SOC Copilot / NIST SP 800-61",
        "tags": [
            "standard:NIST SP 800-61",
            "att&ck:T1048",
            "att&ck:T1567",
            "data_breach",
            "exfiltration",
            "dlp",
            "investigation"
        ],
        "verified": True,
        "featured": False,
        "download_count": 567,
        "rating_average": 4.5,
        "rating_count": 23,
        "review_count": 7,
        "required_plugins": [
            "extract_iocs",
            "http_request",
            "generate_report"
        ],
        "compatible_versions": [
            "0.8.0",
            "0.9.0",
            "1.0.0"
        ],
        "dag_json": {
            "nodes": [
                {
                    "id": "start",
                    "type": "start",
                    "name": "Start"
                },
                {
                    "id": "analyze_logs",
                    "type": "extract_iocs",
                    "name": "Analyze Flow Logs"
                },
                {
                    "id": "block_egress",
                    "type": "http_request",
                    "name": "Cutoff Exfiltration Channel"
                },
                {
                    "id": "report",
                    "type": "generate_report",
                    "name": "Generate Breach Report"
                },
                {
                    "id": "end",
                    "type": "end",
                    "name": "End"
                }
            ],
            "edges": [
                {
                    "source": "start",
                    "target": "analyze_logs"
                },
                {
                    "source": "analyze_logs",
                    "target": "block_egress"
                },
                {
                    "source": "block_egress",
                    "target": "report"
                },
                {
                    "source": "report",
                    "target": "end"
                }
            ]
        },
        "documentation": "# 📤 Data Exfiltration Investigation (数据外发与泄露取证调查)\n\n## 📖 处置标准与依据\n- **国际权威规范**: [NIST SP 800-61 Rev.2](https://csrc.nist.gov/pubs/sp/800/61/r2/final) Section 3.2\n- **攻防技术**: MITRE ATT&CK `T1048` (Exfiltration Over Alternative Protocol)\n\n## 📋 标准处置流程 (SOP)\n1. **隐蔽信道检测**: 侦测 DNS Tunneling、ICMP 载荷数据及未知加密隧道外发；\n2. **出口网关熔断**: 边界安全设备对异常外联通道实施瞬时丢包阻断；\n3. **数据密级评估**: 解析外发数据特征，判定是否涉及用户 PII 个人隐私或核心源码资产；\n4. **启动法务合规报备**: 形成事件初报，记录外发字节数与影响范围。"
    },
    {
        "id": "market-pb-020",
        "name": "Unauthorized Public Cloud Storage Sync",
        "description": "检测到内网工作站自动同步企业代码至未经授权的个人公有云存储（Dropbox / Google Drive / 百度网盘）：阻断网盘上传流量并向合规部门报备。",
        "version": "1.2.0",
        "category": "data_breach",
        "difficulty": "beginner",
        "author_name": "Cloud Security Alliance (CSA)",
        "tags": [
            "standard:CIS",
            "att&ck:T1537",
            "att&ck:T1530",
            "cloud_storage",
            "s3",
            "sync",
            "data_leak",
            "csa"
        ],
        "verified": True,
        "featured": False,
        "download_count": 810,
        "rating_average": 4.6,
        "rating_count": 35,
        "review_count": 9,
        "required_plugins": [
            "http_request",
            "slack_notify"
        ],
        "compatible_versions": [
            "0.8.0",
            "0.9.0",
            "1.0.0"
        ],
        "dag_json": {
            "nodes": [
                {
                    "id": "start",
                    "type": "start",
                    "name": "Start"
                },
                {
                    "id": "block_sync",
                    "type": "http_request",
                    "name": "Block Cloud Storage Egress"
                },
                {
                    "id": "audit_log",
                    "type": "slack_notify",
                    "name": "Notify Security Compliance"
                },
                {
                    "id": "end",
                    "type": "end",
                    "name": "End"
                }
            ],
            "edges": [
                {
                    "source": "start",
                    "target": "block_sync"
                },
                {
                    "source": "block_sync",
                    "target": "audit_log"
                },
                {
                    "source": "audit_log",
                    "target": "end"
                }
            ]
        },
        "documentation": "# ☁️ Unauthorized Public Cloud Storage Sync (未经授权云存储同步拦截)\n\n## 📖 处置标准与依据\n- **国际云安全标准**: [Cloud Security Alliance (CSA) Security Guidance](https://cloudsecurityalliance.org/)\n- **合规标准**: CIS AWS / GCP Foundations Benchmark\n\n## 🛡️ MITRE ATT&CK 映射\n- `T1537 (Transfer Data to Cloud Account)`: 攻击者将企业敏感数据同步至私有外部云账户\n\n## 📋 标准处置流程 (SOP)\n1. **异常 Bucket 关联识别**: 提取同步进程的目标存储桶 ARN，核对其是否在公司企业白名单内；\n2. **云访问策略撤销**: 阻断目标存储桶的网络连通性并吊销同步程序凭据；\n3. **审计日志回溯**: 全量追溯该程序过去 7 天内所读取的文件目录树；\n4. **启动资产清理**: 联动外部云服务商下发滥用与盗窃调查申诉。"
    },
    {
        "id": "market-pb-021",
        "name": "Database Mass Dump & Export Alert Response",
        "description": "生产核心数据库发生单次导出超 10,000 条用户信息事件：比对 DBA 审批申请编号，无对应审批单时即刻阻断会话并锁定数据库连接池。",
        "version": "1.5.0",
        "category": "data_breach",
        "difficulty": "intermediate",
        "author_name": "Database Security Consortium",
        "tags": [
            "standard:PCI-DSS",
            "att&ck:T1567",
            "att&ck:T1005",
            "database",
            "dump",
            "export",
            "pci_dss",
            "gdpr"
        ],
        "verified": True,
        "featured": True,
        "download_count": 1290,
        "rating_average": 4.8,
        "rating_count": 58,
        "review_count": 16,
        "required_plugins": [
            "http_request",
            "human_approval",
            "slack_notify"
        ],
        "compatible_versions": [
            "0.8.0",
            "0.9.0",
            "1.0.0"
        ],
        "dag_json": {
            "nodes": [
                {
                    "id": "start",
                    "type": "start",
                    "name": "Start"
                },
                {
                    "id": "check_approval",
                    "type": "http_request",
                    "name": "Cross-check ITSM Change Ticket"
                },
                {
                    "id": "kill_session",
                    "type": "http_request",
                    "name": "Terminate Active DB Session"
                },
                {
                    "id": "alert_ciso",
                    "type": "slack_notify",
                    "name": "Escalate to CISO Immediate"
                },
                {
                    "id": "end",
                    "type": "end",
                    "name": "End"
                }
            ],
            "edges": [
                {
                    "source": "start",
                    "target": "check_approval"
                },
                {
                    "source": "check_approval",
                    "target": "kill_session"
                },
                {
                    "source": "kill_session",
                    "target": "alert_ciso"
                },
                {
                    "source": "alert_ciso",
                    "target": "end"
                }
            ]
        },
        "documentation": "# 🗄️ Database Mass Dump & Export Alert Response (数据库全量导出告警阻断)\n\n## 📖 处置标准与依据\n- **合规标准**: [PCI-DSS 4.0 Requirement 3 & 10](https://www.pcisecuritystandards.org/)\n- **法规要求**: GDPR Article 33 泄露通报准备\n\n## 📋 标准处置流程 (SOP)\n1. **高危 SQL 识别**: 捕获数据库未带过滤条件的 `SELECT *` 大结果集或 `mysqldump` 行为；\n2. **数据库会话强杀**: 数据库审计代理（DAM）或网关自动终止该客户端 Session 连接；\n3. **受影响数据统计**: 精确统计涉及持卡人信息、手机号或身份证号的行数；\n4. **合规响应激活**: 启动 72 小时数据泄露调查倒计时并通报安全委员会。"
    },
    {
        "id": "market-pb-007",
        "name": "GDPR & Data Compliance Breach Notification",
        "description": "面向数据合规性审计与泄露事故的合规处置流：依据等保/GDPR 72小时申报规范，自动化核验受影响用户范围、留存加密证据链并发送通报。",
        "version": "1.0.0",
        "category": "compliance",
        "difficulty": "intermediate",
        "author_name": "SOC Copilot / EU Privacy Office",
        "tags": [
            "standard:ISO 27035",
            "compliance:GDPR-Art33",
            "compliance:ISO-27701",
            "gdpr",
            "compliance",
            "notification",
            "legal"
        ],
        "verified": True,
        "featured": False,
        "download_count": 756,
        "rating_average": 4.6,
        "rating_count": 28,
        "review_count": 8,
        "required_plugins": [
            "generate_report",
            "slack_notify"
        ],
        "compatible_versions": [
            "0.8.0",
            "0.9.0",
            "1.0.0"
        ],
        "dag_json": {
            "nodes": [
                {
                    "id": "start",
                    "type": "start",
                    "name": "Start"
                },
                {
                    "id": "assess",
                    "type": "generate_report",
                    "name": "Compile Compliance Evidence"
                },
                {
                    "id": "notify",
                    "type": "slack_notify",
                    "name": "Dispatch Legal Alert"
                },
                {
                    "id": "end",
                    "type": "end",
                    "name": "End"
                }
            ],
            "edges": [
                {
                    "source": "start",
                    "target": "assess"
                },
                {
                    "source": "assess",
                    "target": "notify"
                },
                {
                    "source": "notify",
                    "target": "end"
                }
            ]
        },
        "documentation": "# ⚖️ GDPR & Data Compliance Breach Notification (GDPR 合规 72 小时应急通报)\n\n## 📖 处置标准与依据\n- **国际法律法规**: [EU GDPR Regulation (EU) 2016/679 Article 33 & 34](https://gdpr-info.eu/art-33-gdpr/)\n- **国际标准**: [ISO/IEC 27035](https://www.iso.org/standard/60803.html) & [ISO/IEC 27701](https://www.iso.org/standard/71670.html)\n\n## 📋 标准处置流程 (SOP)\n1. **数据泄露事实确认**: 确认发生个人数据被非授权访问、泄露或损坏；\n2. **风险评估矩阵**: 评估对受影响数据主体权利和自由产生风险的严重程度；\n3. **通报监管机构**: 在知悉事件后 72 小时内，自动化生成正式合规报告递交对应监管机构（DPA）；\n4. **受影响个人告知**: 若存在高风险，拟定告知函及时向所有受影响用户发出通报并提供补救措施。"
    },
    {
        "id": "market-pb-022",
        "name": "PCI-DSS Automated Quarterly Firewall Audit",
        "description": "自动化执行 PCI-DSS 6.4 条款防火墙规则审查：扫描全网边界设备中 Any-Any 放行规则、过时临时策略，自动归档并生成审计证据包。",
        "version": "1.0.0",
        "category": "compliance",
        "difficulty": "intermediate",
        "author_name": "PCI Security Standards Council",
        "tags": [
            "standard:PCI-DSS",
            "standard:CIS",
            "compliance:PCI-DSS-Req1",
            "pci_dss",
            "firewall",
            "audit",
            "compliance"
        ],
        "verified": False,
        "featured": False,
        "download_count": 670,
        "rating_average": 4.5,
        "rating_count": 24,
        "review_count": 6,
        "required_plugins": [
            "http_request",
            "generate_report"
        ],
        "compatible_versions": [
            "0.8.0",
            "0.9.0",
            "1.0.0"
        ],
        "dag_json": {
            "nodes": [
                {
                    "id": "start",
                    "type": "start",
                    "name": "Start"
                },
                {
                    "id": "pull_rules",
                    "type": "http_request",
                    "name": "Dump Firewall Rule Tables"
                },
                {
                    "id": "find_any_any",
                    "type": "http_request",
                    "name": "Flag Overly Permissive Policies"
                },
                {
                    "id": "export_pdf",
                    "type": "generate_report",
                    "name": "Generate PCI Compliance Report"
                },
                {
                    "id": "end",
                    "type": "end",
                    "name": "End"
                }
            ],
            "edges": [
                {
                    "source": "start",
                    "target": "pull_rules"
                },
                {
                    "source": "pull_rules",
                    "target": "find_any_any"
                },
                {
                    "source": "find_any_any",
                    "target": "export_pdf"
                },
                {
                    "source": "export_pdf",
                    "target": "end"
                }
            ]
        },
        "documentation": "# 📋 PCI-DSS Automated Quarterly Firewall Audit (PCI-DSS 防火墙策略季度巡检)\n\n## 📖 处置标准与依据\n- **支付安全权威标准**: [PCI-DSS 4.0 Requirement 1](https://www.pcisecuritystandards.org/) (Install and Maintain Network Security Controls)\n- **行业安全基线**: CIS Benchmark for Network Devices\n\n## 📋 标准处置流程 (SOP)\n1. **策略全量遍历**: 遍历边界防火墙、虚拟私有网络及云安全组全量规则清单；\n2. **违规策略筛查**: 自动高亮源或目的为 Any-Any、缺乏业务备注或超过 180 天未更新的规则；\n3. **合规得分统计**: 计算 PCI-DSS 网络安全合规度评分；\n4. **下发清理工单**: 自动在工单系统向网络安全工程师派发废弃规则下线审核任务。"
    },
    {
        "id": "market-pb-023",
        "name": "Expired SSL/TLS Certificate Auto-Renewal Check",
        "description": "生产网全部域名与网关证书到期提前 30 天预警与自动化核验：针对 Let's Encrypt / ACME 协议自动触发续签测试，防止业务因证书失效中断。",
        "version": "1.3.0",
        "category": "compliance",
        "difficulty": "beginner",
        "author_name": "Internet Engineering Task Force (IETF)",
        "tags": [
            "standard:NIST SP 800-52",
            "compliance:NIST-800-52",
            "compliance:RFC-8446",
            "ssl",
            "tls",
            "certificate",
            "renewal"
        ],
        "verified": True,
        "featured": False,
        "download_count": 1120,
        "rating_average": 4.7,
        "rating_count": 47,
        "review_count": 12,
        "required_plugins": [
            "http_request",
            "slack_notify"
        ],
        "compatible_versions": [
            "0.8.0",
            "0.9.0",
            "1.0.0"
        ],
        "dag_json": {
            "nodes": [
                {
                    "id": "start",
                    "type": "start",
                    "name": "Start"
                },
                {
                    "id": "probe_cert",
                    "type": "http_request",
                    "name": "Probe Domain SSL Expiration"
                },
                {
                    "id": "renew_cert",
                    "type": "http_request",
                    "name": "Call ACME Renewal API"
                },
                {
                    "id": "notify_devops",
                    "type": "slack_notify",
                    "name": "Send Certificate Health Status"
                },
                {
                    "id": "end",
                    "type": "end",
                    "name": "End"
                }
            ],
            "edges": [
                {
                    "source": "start",
                    "target": "probe_cert"
                },
                {
                    "source": "probe_cert",
                    "target": "renew_cert"
                },
                {
                    "source": "renew_cert",
                    "target": "notify_devops"
                },
                {
                    "source": "notify_devops",
                    "target": "end"
                }
            ]
        },
        "documentation": "# 🔒 Expired SSL/TLS Certificate Auto-Renewal Check (SSL/TLS 证书到期巡检与续签)\n\n## 📖 处置标准与依据\n- **行业权威规范**: [NIST SP 800-52 Rev.2](https://csrc.nist.gov/pubs/sp/800/52/r2/final) (Guidelines for the Selection and Use of TLS)\n- **互联网标准**: RFC 8446 (The Transport Layer Security Protocol Version 1.3)\n\n## 📋 标准处置流程 (SOP)\n1. **全网域名证书巡检**: 定期握手扫描企业对外发布的所有域名及 API 端点证书有效期限；\n2. **到期阈值警报**: 筛选出有效天数小于 30 天的证书资产；\n3. **ACME 自动化续签**: 联动 Let's Encrypt / 内部 CA 机构发起自动化验证并签发新证书；\n4. **证书热重载部署**: 自动分发至 Nginx / 云负载均衡器热重载，并校验证书链完整度。"
    },
    {
        "id": "market-pb-008",
        "name": "Cloud Native K8s Container Isolation",
        "description": "云原生与容器环境逃逸告警响应剧本：自动下发 NetworkPolicy 隔离目标 Pod、抓取容器运行日志与内存转储、通知 SRE 团队处置。",
        "version": "1.3.0",
        "category": "custom",
        "difficulty": "intermediate",
        "author_name": "CNCF Cloud Native Security Group",
        "tags": [
            "standard:MITRE ATT&CK",
            "att&ck:T1611",
            "att&ck:T1610",
            "k8s",
            "kubernetes",
            "container",
            "isolation",
            "cloud_native"
        ],
        "verified": True,
        "featured": False,
        "download_count": 940,
        "rating_average": 4.7,
        "rating_count": 41,
        "review_count": 10,
        "required_plugins": [
            "http_request",
            "slack_notify"
        ],
        "compatible_versions": [
            "0.8.0",
            "0.9.0",
            "1.0.0"
        ],
        "dag_json": {
            "nodes": [
                {
                    "id": "start",
                    "type": "start",
                    "name": "Start"
                },
                {
                    "id": "isolate_pod",
                    "type": "http_request",
                    "name": "Apply K8s NetworkPolicy"
                },
                {
                    "id": "dump_logs",
                    "type": "http_request",
                    "name": "Dump Pod Container Logs"
                },
                {
                    "id": "notify_sre",
                    "type": "slack_notify",
                    "name": "Page SRE On-call"
                },
                {
                    "id": "end",
                    "type": "end",
                    "name": "End"
                }
            ],
            "edges": [
                {
                    "source": "start",
                    "target": "isolate_pod"
                },
                {
                    "source": "isolate_pod",
                    "target": "dump_logs"
                },
                {
                    "source": "dump_logs",
                    "target": "notify_sre"
                },
                {
                    "source": "notify_sre",
                    "target": "end"
                }
            ]
        },
        "documentation": "# ☸️ Cloud Native K8s Container Isolation (K8s 容器逃逸应急隔离)\n\n## 📖 处置标准与依据\n- **云原生官方规范**: [CNCF Cloud Native Security Whitepaper](https://www.cncf.io/)\n- **攻防标准**: MITRE ATT&CK for Containers (`T1611` Escape to Host)\n\n## 📋 标准处置流程 (SOP)\n1. **容器逃逸行为侦测**: Falco 捕获容器尝试挂载宿主机敏感目录 `/proc` 或写入内核模块；\n2. **网络策略瞬时阻断**: 自动下发 Kubernetes NetworkPolicy 将目标 Pod 的 Ingress/Egress 完全封堵；\n3. **内存快照保全**: 对目标 Container 触发 coredump 并抽取镜像层差异以保全现场证据；\n4. **安全销毁与驱逐**: 优雅驱逐被入侵 Pod，并排查同节点其他容器健康状态。"
    },
    {
        "id": "market-pb-024",
        "name": "AWS Root Account Login Without MFA Remediation",
        "description": "检测到 AWS 主根账号（Root User）通过控制台直接登录且未绑定 MFA：自动向企业微信/钉钉/PagerDuty 广播告警、强制吊销临时凭据并上锁管理。",
        "version": "2.1.0",
        "category": "custom",
        "difficulty": "advanced",
        "author_name": "AWS Security Best Practices Standard",
        "tags": [
            "standard:AWS Best Practices",
            "standard:CIS",
            "att&ck:T1078.004",
            "compliance:CIS-AWS-1.5",
            "aws",
            "iam",
            "root",
            "mfa",
            "cloud"
        ],
        "verified": True,
        "featured": True,
        "download_count": 2780,
        "rating_average": 4.9,
        "rating_count": 98,
        "review_count": 29,
        "required_plugins": [
            "http_request",
            "slack_notify"
        ],
        "compatible_versions": [
            "0.8.0",
            "0.9.0",
            "1.0.0"
        ],
        "dag_json": {
            "nodes": [
                {
                    "id": "start",
                    "type": "start",
                    "name": "Start"
                },
                {
                    "id": "parse_cloudtrail",
                    "type": "extract_iocs",
                    "name": "Extract AWS CloudTrail Event"
                },
                {
                    "id": "revoke_session",
                    "type": "http_request",
                    "name": "Revoke AWS Console Sessions"
                },
                {
                    "id": "notify_soc",
                    "type": "slack_notify",
                    "name": "Broadcast Root Alert to SecOps"
                },
                {
                    "id": "end",
                    "type": "end",
                    "name": "End"
                }
            ],
            "edges": [
                {
                    "source": "start",
                    "target": "parse_cloudtrail"
                },
                {
                    "source": "parse_cloudtrail",
                    "target": "revoke_session"
                },
                {
                    "source": "revoke_session",
                    "target": "notify_soc"
                },
                {
                    "source": "notify_soc",
                    "target": "end"
                }
            ]
        },
        "documentation": """# ☁️ AWS Root Account Login Without MFA Remediation (AWS 根账号无MFA告警处置)

## 📖 处置标准与依据
- **云厂商权威规范**: [AWS Well-Architected Security Pillar](https://aws.amazon.com/architecture/well-architected/)
- **行业安全基线**: CIS AWS Foundations Benchmark v3.0 (Requirement 1.5 & 1.6)

## 🛡️ MITRE ATT&CK 映射
- `T1078.004 (Cloud Accounts)`: 云特权根账号被非授权利用

## 📋 标准处置流程 (SOP)
1. **CloudTrail 事件监听**: EventBridge 实时捕获 `ConsoleLogin` 事件且用户类型为 `Root`；
2. **MFA 状态校验**: 检查该登录是否通过了硬件/虚拟 MFA 双因子校验；
3. **强制注销活跃会话**: 未经双因子校验的登录直接通过 IAM API 吊销活跃控制台 Session 并使其 Access Key 失效；
4. **P0 紧急通报**: 触发严重等级警报，向 CISO 和云基础设施架构师发送紧急安全提醒。""",
    }
]


# ── 数据库同步逻辑 ──

def seed_database(engine, db_name="DB"):
    print(f"📦 正在向 {db_name} 初始化官方剧本市场数据 ({len(OFFICIAL_PLAYBOOKS)} 套剧本)...")
    with engine.begin() as conn:
        for pb in OFFICIAL_PLAYBOOKS:
            exists = conn.execute(
                text("SELECT id FROM marketplace_playbooks WHERE id = :id"),
                {"id": pb["id"]},
            ).scalar()
            
            if exists:
                conn.execute(
                    text("""
                        UPDATE marketplace_playbooks
                        SET name = :name,
                            description = :description,
                            version = :version,
                            category = :category,
                            difficulty = :difficulty,
                            tags = :tags,
                            author_name = :author_name,
                            dag_json = :dag_json,
                            documentation = :documentation,
                            status = 'approved',
                            verified = :verified,
                            featured = :featured,
                            download_count = :download_count,
                            rating_average = :rating_average,
                            rating_count = :rating_count,
                            review_count = :review_count,
                            required_plugins = :required_plugins,
                            compatible_versions = :compatible_versions,
                            updated_at = :updated_at
                        WHERE id = :id
                    """),
                    {
                        "id": pb["id"],
                        "name": pb["name"],
                        "description": pb["description"],
                        "version": pb["version"],
                        "category": pb["category"],
                        "difficulty": pb["difficulty"],
                        "tags": json.dumps(pb["tags"]),
                        "author_name": pb["author_name"],
                        "dag_json": json.dumps(pb["dag_json"]),
                        "documentation": pb["documentation"],
                        "verified": pb["verified"],
                        "featured": pb["featured"],
                        "download_count": pb["download_count"],
                        "rating_average": pb["rating_average"],
                        "rating_count": pb["rating_count"],
                        "review_count": pb["review_count"],
                        "required_plugins": json.dumps(pb["required_plugins"]),
                        "compatible_versions": json.dumps(pb["compatible_versions"]),
                        "updated_at": NOW,
                    },
                )
            else:
                conn.execute(
                    text("""
                        INSERT INTO marketplace_playbooks (
                            id, name, description, version, category, difficulty, tags,
                            author_name, dag_json, documentation, status,
                            verified, featured, download_count, rating_average,
                            rating_count, review_count, required_plugins,
                            compatible_versions, created_at, updated_at
                        ) VALUES (
                            :id, :name, :description, :version, :category, :difficulty, :tags,
                            :author_name, :dag_json, :documentation, 'approved',
                            :verified, :featured, :download_count, :rating_average,
                            :rating_count, :review_count, :required_plugins,
                            :compatible_versions, :created_at, :updated_at
                        )
                    """),
                    {
                        "id": pb["id"],
                        "name": pb["name"],
                        "description": pb["description"],
                        "version": pb["version"],
                        "category": pb["category"],
                        "difficulty": pb["difficulty"],
                        "tags": json.dumps(pb["tags"]),
                        "author_name": pb["author_name"],
                        "dag_json": json.dumps(pb["dag_json"]),
                        "documentation": pb["documentation"],
                        "verified": pb["verified"],
                        "featured": pb["featured"],
                        "download_count": pb["download_count"],
                        "rating_average": pb["rating_average"],
                        "rating_count": pb["rating_count"],
                        "review_count": pb["review_count"],
                        "required_plugins": json.dumps(pb["required_plugins"]),
                        "compatible_versions": json.dumps(pb["compatible_versions"]),
                        "created_at": NOW - timedelta(days=15),
                        "updated_at": NOW,
                    },
                )
        print(f"✅ {db_name} 初始化完成，共导入 {len(OFFICIAL_PLAYBOOKS)} 套官方精选剧本！")


if __name__ == "__main__":
    try:
        pg_engine = create_engine(PG_URL)
        seed_database(pg_engine, "PostgreSQL (仿真环境)")
    except Exception as e:
        print(f"⚠️ PostgreSQL 初始化失败: {e}")

    try:
        sqlite_engine = create_engine(SQLITE_URL)
        seed_database(sqlite_engine, "SQLite (本地开发库)")
    except Exception as e:
        print(f"⚠️ SQLite 初始化失败: {e}")
