"""Enrich all 24 marketplace playbooks with authoritative standards, MITRE ATT&CK tags,
and comprehensive Markdown SOP documentation.
Updates both PostgreSQL (sim container) and SQLite (local dev).
"""

import json
import os
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy import create_engine, text
from scripts.seed_marketplace import OFFICIAL_PLAYBOOKS

PG_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://soc_sim_user:soc_sim_password_123456@127.0.0.1:15432/soc_sim_db",
)
SQLITE_URL = "sqlite:///data/app.db"

# Master mapping for 24 playbooks
ENRICHMENTS = {
    "market-pb-001": {
        "author_name": "SOC Copilot / NIST SP 800-61",
        "tags": ["standard:NIST SP 800-61", "att&ck:T1566.001", "att&ck:T1566.002", "phishing", "email", "ioc", "blocking", "otx"],
        "documentation": """# 🎣 Phishing Email Auto-Response (鱼叉钓鱼邮件自动化响应)

## 📖 处置标准与依据
- **国际权威标准**: [NIST SP 800-61 Rev.2](https://csrc.nist.gov/pubs/sp/800/61/r2/final) (计算机安全事件处置指南 Section 3.2: Detection & Analysis)
- **攻防矩阵归属**: MITRE ATT&CK Enterprise Matrix
- **剧本维护组织**: SOC Copilot 官方核心安全团队

## 🛡️ MITRE ATT&CK 映射
| 战术阶段 | 技术编号 | 技术名称 | 处置动作 |
| :--- | :--- | :--- | :--- |
| **Initial Access (初始访问)** | `T1566.001` | Spearphishing Attachment | 提取附件哈希并隔离 |
| **Initial Access (初始访问)** | `T1566.002` | Spearphishing Link | 提取 URL 并下发网关黑名单 |
| **Execution (执行)** | `T1204.001` | Malicious Link | 告警受影响用户并撤回邮件 |

## 🎯 触发条件与适用范围
- 邮件网关 (SEG) 检测到未通过 SPF/DKIM/DMARC 校验的高风险外发邮件；
- 终端安全软件报出恶意链接点击重定向事件；
- 企业员工通过 Outlook / Webmail 插件自主上报可疑鱼叉钓鱼告警。

## 📋 标准应急响应处置流 (SOP)
1. **取证与特征提取**:
   - 自动解析原始 EML/MSG 报文，提取发送源 IP、真实发件人、邮件主题及所有内嵌超链接与附件；
2. **多源情报富化 (Threat Intel Enrichment)**:
   - 调用 AlienVault OTX、VirusTotal 查询发信 IP 与 URL 域名声誉及历史恶意家族标注；
3. **网关阻断与全网遏制**:
   - 联动边界防火墙与邮件安全网关下发黑名单规则；
   - 检索全网邮箱，以 Message-ID 为索引批量撤回所有相同投递邮件；
4. **受害者协同与补救**:
   - 针对已点击链接的用户强制注销当前 Web Session 并重置密码；
   - 自动发送安全教育警示提示用户防范高仿欺诈。
""",
    },
    "market-pb-009": {
        "author_name": "Cyber Defense Labs / MITRE ATT&CK",
        "tags": ["standard:MITRE ATT&CK", "att&ck:T1566", "att&ck:T1589", "bec", "phishing", "executive", "financial"],
        "documentation": """# 👔 Executive BEC Spear-Phishing Triage (高管商务邮件欺诈研判)

## 📖 处置标准与依据
- **国际权威标准**: [FBI IC3 BEC Advisory](https://www.ic3.gov/) & [MITRE ATT&CK T1566](https://attack.mitre.org/techniques/T1566/)
- **合规指引**: 针对针对财务转账的高危假冒高管攻击（Business Email Compromise）

## 🛡️ MITRE ATT&CK 映射
- `T1566 (Phishing)`: 诱骗员工实施非受信业务操作
- `T1589 (Gather Victim Identity Information)`: 攻击者收集内部高管职位与日程安排

## 🎯 触发条件
- 外部邮件发件人显示名称与企业内部 C-Level 高管姓名完全一致，但实际发信域为外部免费邮箱或相似域名；
- 邮件正文中包含“加急转账”、“秘密收购”、“财务汇款审批”等高危敏感词汇。

## 📋 标准处置流程 (SOP)
1. **DMARC & 报头深度核验**: 检查邮件头原始 Received 链条，确认是否存在第三方中继或伪造；
2. **相似李鬼域名识别**: 使用编辑距离算法比对发信域名与企业官方域名的字符差异；
3. **财务流紧急阻断**: 自动向财务 ERP 系统下发拦截标记，暂时冻结 30 分钟内针对该账户的在途审批；
4. **线下双人鉴权复核**: 触发语音电话或企业微信安全通道联系高管本人核实真实性。
""",
    },
    "market-pb-010": {
        "author_name": "Palo Alto Cortex Community",
        "tags": ["standard:Cortex XSOAR", "att&ck:T1204.002", "att&ck:T1059", "attachment", "sandbox", "antivirus", "macro"],
        "documentation": """# 💣 Malicious Attachment Detonation Pipeline (恶意附件自动化沙箱引爆)

## 📖 处置标准与依据
- **行业生态标准**: [Palo Alto Cortex XSOAR Playbook Reference](https://xsoar.pan.dev/)
- **规范体系**: 遵循 CISA 恶意文件分析与处置流水线规范

## 🛡️ MITRE ATT&CK 映射
- `T1204.002 (Malicious File)`: 用户诱骗执行 Office 宏或嵌入式可执行载荷
- `T1059 (Command and Scripting Interpreter)`: 宏代码拉起 PowerShell/CMD 执行下一阶段载荷

## 📋 标准处置流程 (SOP)
1. **附件提取与解包**: 自动剥离邮件中的未知 zip/rar/7z 压缩包及 Office 宏文档；
2. **多引擎云端杀毒**: 调用主流杀毒引擎比对静态特征，计算 SHA256；
3. **云沙箱动态引爆**: 自动化提交至沙箱，监控进程创建、注册表自启动项添加及可疑外联 IP；
4. **全网邮件隔离**: 确认恶意后，秒级从邮件服务器邮箱中清除附件并全网分发告警。
""",
    },
    "market-pb-002": {
        "author_name": "SOC Copilot / NIST SP 800-61",
        "tags": ["standard:NIST SP 800-61", "att&ck:T1486", "att&ck:T1489", "ransomware", "emergency", "containment", "forensics", "edr"],
        "documentation": """# 🚨 Ransomware Emergency Containment (勒索病毒应急遏制黄金5分钟)

## 📖 处置标准与依据
- **权威标准**: [NIST SP 800-61 Rev.2](https://csrc.nist.gov/pubs/sp/800/61/r2/final) (Section 3.3: Containment, Eradication, and Recovery)
- **国家指引**: CISA & FBI #StopRansomware 指南

## 🛡️ MITRE ATT&CK 映射
- `T1486 (Data Encrypted for Impact)`: 攻击者批量加密本地与网络共享文件
- `T1489 (Service Stop)`: 攻击者恶意停止数据库与核心关键服务
- `T1490 (Inhibit System Recovery)`: 破坏系统恢复能力

## 📋 标准应急响应处置流 (SOP)
1. **网络秒级断开 (Host Isolation)**:
   - 立即通过 EDR 下发单机网络隔离策略，仅保留管理心跳端口，阻断内网横向加密；
2. **凭据冻结 (Credential Revocation)**:
   - 自动禁用该主机最近登录的所有 AD 域账号与本地管理员会话；
3. **内存与磁盘保全 (Forensic Snapshot)**:
   - 触发虚拟化底座或物理盘只读快照，保全被加密前的内存镜像与关键事件日志；
4. **激活紧急应急指挥部**:
   - 自动在通信群组（Slack/钉钉/企业微信）拉起指挥通道，向 CISO 和安全值班负责人广播。
""",
    },
    "market-pb-011": {
        "author_name": "SANS DFIR Guild",
        "tags": ["standard:MITRE ATT&CK", "att&ck:T1490", "vss", "shadow_copy", "ransomware", "backup", "edr"],
        "documentation": """# 🛡️ Shadow Copy & VSS Tampering Defense (卷影副本防篡改防御)

## 📖 处置标准与依据
- **国际权威标准**: [MITRE ATT&CK T1490](https://attack.mitre.org/techniques/T1490/) (Inhibit System Recovery)
- **实战指南**: SANS DFIR 勒索软件阻断对抗实录

## 🎯 典型攻击特征
- 攻击者通过 `vssadmin delete shadows /all /quiet` 或 `wmic shadowcopy delete` 企图剥夺受害者的自愈还原能力。

## 📋 标准处置流程 (SOP)
1. **特权进程瞬时阻断**: EDR 拦截到调用卷影删除指令的瞬间，直接强杀发起进程；
2. **异地不可篡改冷备锁定**: 联动企业存储集群（WORM 存储 / NAS），进入只读保护状态；
3. **提升严重等级**: 将告警等级提升至 P0（Critical Pre-cursor），通报应急响应专家进场排查。
""",
    },
    "market-pb-012": {
        "author_name": "Europol NoMoreRansom Project",
        "tags": ["standard:ISO 27035", "att&ck:T1486", "ransomware", "restoration", "decryption", "backup"],
        "documentation": """# 🔑 Ransomware Decryption & System Restoration (勒索灾后恢复与密钥匹配)

## 📖 处置标准与依据
- **开源标准倡议**: [NoMoreRansom.org](https://www.nomoreransom.org/)
- **合规标准**: [ISO/IEC 27035](https://www.iso.org/standard/60803.html) 信息安全事件管理与灾难恢复规范

## 📋 标准处置流程 (SOP)
1. **勒索家族识别**: 读取勒索信特征及被加密文件后缀，比对全球已知勒索变种；
2. **解密工具检索**: 自动化检索 NoMoreRansom 开源公私钥库，尝试解密样本验证成功率；
3. **干净还原点人工审批**: 列出被感染前最近一份可信快照，由基础设施团队双人审批签字；
4. **编排还原执行**: 自动化下发还原镜像，并进行代码和系统安全基线扫描后重新入网。
""",
    },
    "market-pb-003": {
        "author_name": "SOC Copilot / NIST SP 800-61",
        "tags": ["standard:NIST SP 800-61", "att&ck:T1204", "att&ck:T1059", "malware", "sandbox", "quarantine", "edr"],
        "documentation": """# 🦠 Malware Analysis & Quarantine (恶意代码自动化研判与隔离)

## 📖 处置标准与依据
- **国际权威标准**: [NIST SP 800-61 Rev.2](https://csrc.nist.gov/pubs/sp/800/61/r2/final)
- **攻防标准**: MITRE ATT&CK Enterprise Matrix

## 🛡️ MITRE ATT&CK 映射
- `T1204 (User Execution)`: 恶意代码被执行
- `T1059 (Command and Scripting Interpreter)`: 脚本与命令行执行

## 📋 标准处置流程 (SOP)
1. **端点样本抓取**: 从端点提取可疑样本文件及启动项参数；
2. **威胁情报查询**: 查询各大公私情报库计算哈希信誉分；
3. **端点处置落地**: 判定恶意后，EDR 自动粉碎目标文件，回滚注册表改动；
4. **全网免疫防护**: 自动生成 Yara / IOC 规则推送到全网所有防护探针。
""",
    },
    "market-pb-013": {
        "author_name": "Splunk SOAR Community",
        "tags": ["standard:MITRE ATT&CK", "att&ck:T1071.001", "att&ck:T1573", "cobalt_strike", "c2", "beacon", "ja3"],
        "documentation": """# 📡 Cobalt Strike Beacon C2 Triage (C2 远控信标研判与阻断)

## 📖 处置标准与依据
- **行业剧本标准**: [Splunk SOAR Community Playbooks](https://research.splunk.com/)
- **攻防标准**: MITRE ATT&CK T1071.001 (Application Layer Protocol: Web Protocols)

## 🛡️ MITRE ATT&CK 映射
- `T1071.001 (Web Protocols)`: 使用 HTTP/HTTPS 伪装为正常业务流量与远控服务端通信
- `T1573 (Encrypted Channel)`: 双向非对称加密传输指令

## 📋 标准处置流程 (SOP)
1. **流量抖动与周期性分析**: 深度解析通信包间隔与 Jitter 规律，提取 JA3 TLS 指纹；
2. **DNS 沉洞拦截**: 边界 DNS 服务器将 C2 域名指向内网安全沉洞（Sinkhole）抓取受害者 IP；
3. **内存转储取证**: 触发受害终端 EDR 提取关键进程内存 Dump 留存；
4. **阻断升级**: 防火墙秒级封禁远程服务端 IP 端口。
""",
    },
    "market-pb-014": {
        "author_name": "Application Security Guild / OWASP",
        "tags": ["standard:OWASP Top 10", "att&ck:T1505.003", "webshell", "memory_horse", "backdoor", "waf", "java"],
        "documentation": """# 🗡️ WebShell & Memory Horse Backdoor Purge (后门与内存马彻底清除)

## 📖 处置标准与依据
- **行业权威规范**: [OWASP Top 10 A03:2021 Injection](https://owasp.org/Top10/)
- **攻防技术**: MITRE ATT&CK `T1505.003` (Server Software Component: Web Shell)

## 📋 标准处置流程 (SOP)
1. **静态基线哈希比对**: 快速遍历 Web 根目录，比对 Git 纯净版本库排查新增与篡改脚本；
2. **负载均衡摘除**: 将被入侵的业务服务器从集群 Load Balancer 中摘除，避免脏流量继续处理；
3. **内存马排查与卸载**: 排查 Java Filter/Servlet/Listener 动态注入项，调用 Agent 卸载恶意字节码；
4. **重置部署**: 清除后门后重新从 CI/CD 干净构建制品重新发布。
""",
    },
    "market-pb-006": {
        "author_name": "SOC Copilot / MITRE ATT&CK",
        "tags": ["standard:MITRE ATT&CK", "att&ck:T1110", "bruteforce", "ssh", "rdp", "firewall", "ip_ban"],
        "documentation": """# 🔨 Brute Force Defense & Dynamic Blacklist (暴力破解动态封禁)

## 📖 处置标准与依据
- **国际权威规范**: [MITRE ATT&CK T1110](https://attack.mitre.org/techniques/T1110/) (Brute Force)
- **处置指引**: NIST SP 800-61 Section 3.2: Automated Network Containment

## 📋 标准处置流程 (SOP)
1. **爆破特征提取**: 聚合统计单位时间内来自同一源 IP 对 SSH/RDP/Web 接口的失败次数；
2. **动态黑名单下发**: 超过阈值后自动调用边缘防火墙 / API 网关封禁攻击源 24 小时；
3. **成功登录校验**: 排查同一 IP 是否存在一次“登录成功”记录，若存在则立即冻结该账号并强制踢下线；
4. **事件闭单与通报**: 记录工单并向运维安全组通报高风险账号。
""",
    },
    "market-pb-015": {
        "author_name": "Cloudflare Defense Guidelines",
        "tags": ["standard:NIST SP 800-61", "att&ck:T1498", "ddos", "waf", "scrubbing", "rate_limit"],
        "documentation": """# 🌊 High-Volume DDoS Mitigation & WAF Sync (大流量 DDoS 缓解清洗)

## 📖 处置标准与依据
- **网络防御架构**: Cloudflare Anycast DDoS Mitigation Guidelines
- **应急标准**: NIST SP 800-61 Rev.2

## 🛡️ MITRE ATT&CK 映射
- `T1498 (Network Denial of Service)`: 制造网络服务不可用

## 📋 标准处置流程 (SOP)
1. **异常流量激增告警**: 监控边界入向带宽与 SYN/UDP 包比率激增事件；
2. **一键切换云端高防清洗**: 自动更新 BGP 宣告，将流量牵引至云清洗中心过滤脏流量；
3. **WAF 启用交互挑战**: 开启针对应用层 HTTP Flood 的 JS Challenge 与验证码机制；
4. **源站保护校验**: 确保护盾源站仅响应清洗中心回源 IP，拦截直接针对源站的嗅探。
""",
    },
    "market-pb-016": {
        "author_name": "Cloud Threat Research / MITRE ATT&CK",
        "tags": ["standard:MITRE ATT&CK", "att&ck:T1496", "cryptomining", "stratum", "firewall", "edr"],
        "documentation": """# ⛏️ Cryptomining Pool Traffic Cutoff (挖矿木马全链路切断)

## 📖 处置标准与依据
- **攻防标准**: [MITRE ATT&CK T1496](https://attack.mitre.org/techniques/T1496/) (Resource Hijacking)
- **安全指引**: CISA 关于企业云主机非法算力占用的防御建议

## 📋 标准处置流程 (SOP)
1. **矿池连接识别**: 捕获主机向外部未知端口发起 Stratum/JSON-RPC 协议流量；
2. **网络边缘拦截**: 边界防火墙秒级封禁远程矿池 IP 与常用挖矿域名；
3. **恶意进程清理**: 识别高 CPU 占用的恶意进程，清理定时任务 crontab 与 systemd 服务单元；
4. **溯源入口加固**: 排查弱口令、Redis 未授权访问或未修补的 RCE 漏洞。
""",
    },
    "market-pb-017": {
        "author_name": "OWASP Foundation Standard",
        "tags": ["standard:OWASP Top 10", "att&ck:T1190", "sqli", "injection", "waf", "database"],
        "documentation": """# 💉 SQL Injection & API Parameter Exploit Block (SQL 注入阻断)

## 📖 处置标准与依据
- **国际应用安全权威**: [OWASP Top 10 A03:2021-Injection](https://owasp.org/Top10/)
- **合规映射**: PCI-DSS Requirement 6.4 (Protect Web Applications)

## 🛡️ MITRE ATT&CK 映射
- `T1190 (Exploit Public-Facing Application)`: 利用公开 Web 应用漏洞

## 📋 标准处置流程 (SOP)
1. **注入 Payload 捕获**: WAF 侦测到 URL/Body 中包含布尔盲注、联合查询或延时注入特征；
2. **IP 动态惩罚与封禁**: 阻断当前请求并将攻击者 IP 列入 WAF 临时封禁池；
3. **数据泄露核验**: 检索数据库审计系统，确认该注入语句是否实际返回敏感数据表数据；
4. **研发协同修复**: 自动导出该接口的详细请求复现数据并指派修复工单。
""",
    },
    "market-pb-005": {
        "author_name": "SOC Copilot / CERT Insider Threat Center",
        "tags": ["standard:CISA", "att&ck:T1078", "att&ck:T1005", "insider_threat", "ueba", "anomaly", "dlp"],
        "documentation": """# 🕵️ Insider Threat & UEBA Anomaly Hunting (内部威胁与异常行为排查)

## 📖 处置标准与依据
- **权威指引**: [CISA Insider Threat Mitigation Guide](https://www.cisa.gov/)
- **研究模型**: CMU CERT Insider Threat Center Architecture

## 🛡️ MITRE ATT&CK 映射
- `T1078 (Valid Accounts)`: 内部员工利用已授权合法账号执行越权操作
- `T1005 (Data from Local System)`: 批量提取本地或网络驱动器资料

## 📋 标准处置流程 (SOP)
1. **UEBA 行为偏离告警**: 捕获员工非正常工作时段的大量下载、异常外发等异常偏离基线事件；
2. **敏感权限动态收敛**: 临时降低该员工访问核心机密数据库的权限等级；
3. **DLP 证据链存证**: 自动归档终端操作录屏、网络流量日志及 USB 外发操作记录；
4. **合规审查通知**: 按照企业人事安全流程，向安全委员会与法务主管提报审批。
""",
    },
    "market-pb-018": {
        "author_name": "Active Directory Security Working Group",
        "tags": ["standard:MITRE ATT&CK", "att&ck:T1550.002", "att&ck:T1558.003", "active_directory", "kerberoasting", "pass_the_hash", "lateral_movement"],
        "documentation": """# 🎫 Pass-the-Hash & Kerberoasting Lateral Defense (哈希传递与黄金票据防御)

## 📖 处置标准与依据
- **国际攻防标准**: [MITRE ATT&CK T1550.002](https://attack.mitre.org/techniques/T1550/002/) & [T1558.003](https://attack.mitre.org/techniques/T1558/003/)
- **合规指引**: Microsoft Security Baselines for Active Directory

## 📋 标准处置流程 (SOP)
1. **域控审计捕获**: 监控 Windows Event ID 4769、4776，侦测 Kerberos 票据请求异常暴增；
2. **账号密码重置与吊销**: 强制重置受害服务账号密码，失效已签发的 Kerberos TGT 票据；
3. **主机 RPC 隔离**: 切断受控主机对内网其他资产的 445/135 端口访问；
4. **特权组审计**: 审查 Domain Admins、Enterprise Admins 特权组成员变动情况。
""",
    },
    "market-pb-019": {
        "author_name": "Zero Trust Identity Defense Group",
        "tags": ["standard:CIS", "att&ck:T1078.002", "att&ck:T1530", "service_account", "off_hours", "data_download", "zero_trust"],
        "documentation": """# 🌙 Off-Hours Mass Data Download by Service Account (非工作时间服务账号批量下载)

## 📖 处置标准与依据
- **行业权威规范**: [CIS Controls v8 Safeguard 6.3](https://www.cisecurity.org/)
- **架构准则**: NIST SP 800-207 Zero Trust Architecture (持续凭据认证)

## 📋 标准处置流程 (SOP)
1. **行为基线比对**: 比对自动化服务账号历史调用频次及时间窗口分布；
2. **API 令牌应急撤回**: 自动吊销当前活跃的 OAuth 访问凭据与临时 STS Token；
3. **外联 IP 定位**: 检查调用源 IP 是否来自未知公网环境，阻断非法网段访问；
4. **责任人双因素确认**: 触发钉钉/企业微信机器人通知该接口负责人确认是否为合规批量任务。
""",
    },
    "market-pb-004": {
        "author_name": "SOC Copilot / NIST SP 800-61",
        "tags": ["standard:NIST SP 800-61", "att&ck:T1048", "att&ck:T1567", "data_breach", "exfiltration", "dlp", "investigation"],
        "documentation": """# 📤 Data Exfiltration Investigation (数据外发与泄露取证调查)

## 📖 处置标准与依据
- **国际权威规范**: [NIST SP 800-61 Rev.2](https://csrc.nist.gov/pubs/sp/800/61/r2/final) Section 3.2
- **攻防技术**: MITRE ATT&CK `T1048` (Exfiltration Over Alternative Protocol)

## 📋 标准处置流程 (SOP)
1. **隐蔽信道检测**: 侦测 DNS Tunneling、ICMP 载荷数据及未知加密隧道外发；
2. **出口网关熔断**: 边界安全设备对异常外联通道实施瞬时丢包阻断；
3. **数据密级评估**: 解析外发数据特征，判定是否涉及用户 PII 个人隐私或核心源码资产；
4. **启动法务合规报备**: 形成事件初报，记录外发字节数与影响范围。
""",
    },
    "market-pb-020": {
        "author_name": "Cloud Security Alliance (CSA)",
        "tags": ["standard:CIS", "att&ck:T1537", "att&ck:T1530", "cloud_storage", "s3", "sync", "data_leak", "csa"],
        "documentation": """# ☁️ Unauthorized Public Cloud Storage Sync (未经授权云存储同步拦截)

## 📖 处置标准与依据
- **国际云安全标准**: [Cloud Security Alliance (CSA) Security Guidance](https://cloudsecurityalliance.org/)
- **合规标准**: CIS AWS / GCP Foundations Benchmark

## 🛡️ MITRE ATT&CK 映射
- `T1537 (Transfer Data to Cloud Account)`: 攻击者将企业敏感数据同步至私有外部云账户

## 📋 标准处置流程 (SOP)
1. **异常 Bucket 关联识别**: 提取同步进程的目标存储桶 ARN，核对其是否在公司企业白名单内；
2. **云访问策略撤销**: 阻断目标存储桶的网络连通性并吊销同步程序凭据；
3. **审计日志回溯**: 全量追溯该程序过去 7 天内所读取的文件目录树；
4. **启动资产清理**: 联动外部云服务商下发滥用与盗窃调查申诉。
""",
    },
    "market-pb-021": {
        "author_name": "Database Security Consortium",
        "tags": ["standard:PCI-DSS", "att&ck:T1567", "att&ck:T1005", "database", "dump", "export", "pci_dss", "gdpr"],
        "documentation": """# 🗄️ Database Mass Dump & Export Alert Response (数据库全量导出告警阻断)

## 📖 处置标准与依据
- **合规标准**: [PCI-DSS 4.0 Requirement 3 & 10](https://www.pcisecuritystandards.org/)
- **法规要求**: GDPR Article 33 泄露通报准备

## 📋 标准处置流程 (SOP)
1. **高危 SQL 识别**: 捕获数据库未带过滤条件的 `SELECT *` 大结果集或 `mysqldump` 行为；
2. **数据库会话强杀**: 数据库审计代理（DAM）或网关自动终止该客户端 Session 连接；
3. **受影响数据统计**: 精确统计涉及持卡人信息、手机号或身份证号的行数；
4. **合规响应激活**: 启动 72 小时数据泄露调查倒计时并通报安全委员会。
""",
    },
    "market-pb-007": {
        "author_name": "SOC Copilot / EU Privacy Office",
        "tags": ["standard:ISO 27035", "compliance:GDPR-Art33", "compliance:ISO-27701", "gdpr", "compliance", "notification", "legal"],
        "documentation": """# ⚖️ GDPR & Data Compliance Breach Notification (GDPR 合规 72 小时应急通报)

## 📖 处置标准与依据
- **国际法律法规**: [EU GDPR Regulation (EU) 2016/679 Article 33 & 34](https://gdpr-info.eu/art-33-gdpr/)
- **国际标准**: [ISO/IEC 27035](https://www.iso.org/standard/60803.html) & [ISO/IEC 27701](https://www.iso.org/standard/71670.html)

## 📋 标准处置流程 (SOP)
1. **数据泄露事实确认**: 确认发生个人数据被非授权访问、泄露或损坏；
2. **风险评估矩阵**: 评估对受影响数据主体权利和自由产生风险的严重程度；
3. **通报监管机构**: 在知悉事件后 72 小时内，自动化生成正式合规报告递交对应监管机构（DPA）；
4. **受影响个人告知**: 若存在高风险，拟定告知函及时向所有受影响用户发出通报并提供补救措施。
""",
    },
    "market-pb-022": {
        "author_name": "PCI Security Standards Council",
        "tags": ["standard:PCI-DSS", "standard:CIS", "compliance:PCI-DSS-Req1", "pci_dss", "firewall", "audit", "compliance"],
        "documentation": """# 📋 PCI-DSS Automated Quarterly Firewall Audit (PCI-DSS 防火墙策略季度巡检)

## 📖 处置标准与依据
- **支付安全权威标准**: [PCI-DSS 4.0 Requirement 1](https://www.pcisecuritystandards.org/) (Install and Maintain Network Security Controls)
- **行业安全基线**: CIS Benchmark for Network Devices

## 📋 标准处置流程 (SOP)
1. **策略全量遍历**: 遍历边界防火墙、虚拟私有网络及云安全组全量规则清单；
2. **违规策略筛查**: 自动高亮源或目的为 Any-Any、缺乏业务备注或超过 180 天未更新的规则；
3. **合规得分统计**: 计算 PCI-DSS 网络安全合规度评分；
4. **下发清理工单**: 自动在工单系统向网络安全工程师派发废弃规则下线审核任务。
""",
    },
    "market-pb-023": {
        "author_name": "Internet Engineering Task Force (IETF)",
        "tags": ["standard:NIST SP 800-52", "compliance:NIST-800-52", "compliance:RFC-8446", "ssl", "tls", "certificate", "renewal"],
        "documentation": """# 🔒 Expired SSL/TLS Certificate Auto-Renewal Check (SSL/TLS 证书到期巡检与续签)

## 📖 处置标准与依据
- **行业权威规范**: [NIST SP 800-52 Rev.2](https://csrc.nist.gov/pubs/sp/800/52/r2/final) (Guidelines for the Selection and Use of TLS)
- **互联网标准**: RFC 8446 (The Transport Layer Security Protocol Version 1.3)

## 📋 标准处置流程 (SOP)
1. **全网域名证书巡检**: 定期握手扫描企业对外发布的所有域名及 API 端点证书有效期限；
2. **到期阈值警报**: 筛选出有效天数小于 30 天的证书资产；
3. **ACME 自动化续签**: 联动 Let's Encrypt / 内部 CA 机构发起自动化验证并签发新证书；
4. **证书热重载部署**: 自动分发至 Nginx / 云负载均衡器热重载，并校验证书链完整度。
""",
    },
    "market-pb-008": {
        "author_name": "CNCF Cloud Native Security Group",
        "tags": ["standard:MITRE ATT&CK", "att&ck:T1611", "att&ck:T1610", "k8s", "kubernetes", "container", "isolation", "cloud_native"],
        "documentation": """# ☸️ Cloud Native K8s Container Isolation (K8s 容器逃逸应急隔离)

## 📖 处置标准与依据
- **云原生官方规范**: [CNCF Cloud Native Security Whitepaper](https://www.cncf.io/)
- **攻防标准**: MITRE ATT&CK for Containers (`T1611` Escape to Host)

## 📋 标准处置流程 (SOP)
1. **容器逃逸行为侦测**: Falco 捕获容器尝试挂载宿主机敏感目录 `/proc` 或写入内核模块；
2. **网络策略瞬时阻断**: 自动下发 Kubernetes NetworkPolicy 将目标 Pod 的 Ingress/Egress 完全封堵；
3. **内存快照保全**: 对目标 Container 触发 coredump 并抽取镜像层差异以保全现场证据；
4. **安全销毁与驱逐**: 优雅驱逐被入侵 Pod，并排查同节点其他容器健康状态。
""",
    },
    "market-pb-024": {
        "author_name": "AWS Security Best Practices Standard",
        "tags": ["standard:AWS Best Practices", "standard:CIS", "att&ck:T1078.004", "compliance:CIS-AWS-1.5", "aws", "iam", "root", "mfa", "cloud"],
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
4. **P0 紧急通报**: 触发严重等级警报，向 CISO 和云基础设施架构师发送紧急安全提醒。
""",
    },
}

def enrich_and_seed():
    print("🚀 开始为 24 套剧本注入权威标准、ATT&CK 编号与专业 Markdown SOP...")
    
    # 1. Update in-memory OFFICIAL_PLAYBOOKS list
    for pb in OFFICIAL_PLAYBOOKS:
        pid = pb["id"]
        if pid in ENRICHMENTS:
            enr = ENRICHMENTS[pid]
            pb["author_name"] = enr["author_name"]
            pb["tags"] = enr["tags"]
            pb["documentation"] = enr["documentation"].strip()

    # 2. Update PostgreSQL (sim environment)
    try:
        pg_engine = create_engine(PG_URL)
        with pg_engine.begin() as conn:
            for pb in OFFICIAL_PLAYBOOKS:
                conn.execute(
                    text("""
                        UPDATE marketplace_playbooks SET
                            author_name = :author_name,
                            tags = :tags,
                            documentation = :documentation,
                            updated_at = :updated_at
                        WHERE id = :id
                    """),
                    {
                        "id": pb["id"],
                        "author_name": pb["author_name"],
                        "tags": json.dumps(pb["tags"]),
                        "documentation": pb["documentation"],
                        "updated_at": datetime.now(UTC),
                    },
                )
        print("✅ PostgreSQL (仿真环境) 24 套剧本已成功富化权威标准与 Markdown 详情！")
    except Exception as e:
        print(f"⚠️ PostgreSQL 富化失败: {e}")

    # 3. Update SQLite (local dev environment)
    try:
        sqlite_engine = create_engine(SQLITE_URL)
        with sqlite_engine.begin() as conn:
            for pb in OFFICIAL_PLAYBOOKS:
                conn.execute(
                    text("""
                        UPDATE marketplace_playbooks SET
                            author_name = :author_name,
                            tags = :tags,
                            documentation = :documentation,
                            updated_at = :updated_at
                        WHERE id = :id
                    """),
                    {
                        "id": pb["id"],
                        "author_name": pb["author_name"],
                        "tags": json.dumps(pb["tags"]),
                        "documentation": pb["documentation"],
                        "updated_at": datetime.now(UTC),
                    },
                )
        print("✅ SQLite (本地环境) 24 套剧本已成功富化权威标准与 Markdown 详情！")
    except Exception as e:
        print(f"⚠️ SQLite 富化失败: {e}")

if __name__ == "__main__":
    enrich_and_seed()
