/**
 * Correlation Rules Localization Dictionary and Helpers
 * 关联分析规则多语言翻译字典与辅助解析工具
 */

export interface RuleLocalization {
  nameZh: string;
  nameEn: string;
  descZh: string;
  descEn: string;
  categoryZh: string;
  categoryEn: string;
}

export const CORRELATION_RULES_I18N: Record<string, RuleLocalization> = {
  // Built-in SIEM Correlation Rules
  "ransomware - multiple encrypted files": {
    nameZh: "勒索软件 - 批量文件加密异常",
    nameEn: "Ransomware - Multiple Encrypted Files",
    descZh: "关联同一资产在 5 分钟内发生的勒索软件多文件批量加密事件",
    descEn:
      "Correlates ransomware-related file encryption events across same asset within 5 minutes",
    categoryZh: "勒索攻击",
    categoryEn: "Ransomware",
  },
  "ddos attack - high volume from same source": {
    nameZh: "DDoS 拒绝服务攻击 - 同源大流量冲击",
    nameEn: "DDoS Attack - High Volume from Same Source",
    descZh: "关联同一源 IP 在 1 分钟内产生的高频突发网络请求",
    descEn: "Correlates high-frequency requests from same source IP within 1 minute",
    categoryZh: "网络冲击",
    categoryEn: "DDoS Attack",
  },
  "malware outbreak - same iocs across assets": {
    nameZh: "恶意软件爆发 - 跨资产同源 IOC 感染",
    nameEn: "Malware Outbreak - Same IOCs Across Assets",
    descZh: "关联 1 小时内跨不同资产命中相同文件哈希或通信域名的恶意软件检出事件",
    descEn:
      "Correlates malware detections with same file hash/domain across different assets within 1 hour",
    categoryZh: "恶意代码",
    categoryEn: "Malware Outbreak",
  },
  "data exfiltration - large data transfer": {
    nameZh: "数据外泄 - 异常大流量传输关联",
    nameEn: "Data Exfiltration - Large Data Transfer",
    descZh: "关联同一用户或 IP 在 5 分钟内发生的异常敏感数据大文件外传事件",
    descEn: "Correlates large data transfer events from the same user/IP within 5 minutes",
    categoryZh: "数据外泄",
    categoryEn: "Data Exfiltration",
  },
  "brute force attack - multiple failed logins": {
    nameZh: "暴力破解攻击 - 多次登录失败聚集",
    nameEn: "Brute Force Attack - Multiple Failed Logins",
    descZh: "关联 5 分钟内来自同一源 IP 或针对同一用户名的连续认证失败尝试",
    descEn:
      "Correlates multiple failed login attempts from the same source IP or username within 5 minutes",
    categoryZh: "凭据访问",
    categoryEn: "Brute Force",
  },
  "lateral movement - unusual asset hopping": {
    nameZh: "横向移动 - 异常跨主机跳板漫游",
    nameEn: "Lateral Movement - Unusual Asset Hopping",
    descZh: "关联同一用户在 10 分钟内针对内网多个高价值资产的异常跨主机凭据认证",
    descEn:
      "Correlates authentication/access events across multiple assets for the same user within 10 minutes",
    categoryZh: "横向移动",
    categoryEn: "Lateral Movement",
  },
  "phishing campaign - same url/domain": {
    nameZh: "钓鱼邮件活动 - 同源恶意链接传播",
    nameEn: "Phishing Campaign - Same URL/Domain",
    descZh: "关联 24 小时内跨多位员工邮箱接收相同恶意 URL 或钓鱼域名的攻击事件",
    descEn:
      "Correlates phishing alerts with same URL or domain across multiple users within 24 hours",
    categoryZh: "社会工程",
    categoryEn: "Phishing Campaign",
  },
  "web application attack - same attack pattern": {
    nameZh: "Web 应用攻击 - 同源攻击模式聚簇",
    nameEn: "Web Application Attack - Same Attack Pattern",
    descZh: "关联 30 分钟内针对同一 Web 目标的高频 SQL 注入、XSS 等模式化攻击",
    descEn:
      "Correlates web attacks (SQLi, XSS, etc.) with same pattern against same target within 30 minutes",
    categoryZh: "应用安全",
    categoryEn: "Web Attack",
  },
  "port scanning - multiple port access": {
    nameZh: "端口扫描探测 - 多端口持续探测",
    nameEn: "Port Scanning - Multiple Port Access",
    descZh: "关联 2 分钟内来自同一来源针对内网主机的多端口快速嗅探探测",
    descEn: "Correlates multiple port access attempts from the same source IP within 2 minutes",
    categoryZh: "网络侦察",
    categoryEn: "Port Scanning",
  },
  "insider threat - after-hours access": {
    nameZh: "内部威胁 - 非工作时段异常登录访问",
    nameEn: "Insider Threat - After-Hours Access",
    descZh: "关联同一账号在非工作时间（深夜/周末）跨多天持续访问敏感资产",
    descEn: "Correlates after-hours access events for the same user across multiple days",
    categoryZh: "内部威胁",
    categoryEn: "Insider Threat",
  },

  // Scenario / Demo Correlation Rules (keyed by ID)
  "rule-account-takeover": {
    nameZh: "云控制台与特权账号接管 (ATO)",
    nameEn: "Cloud Console & Account Takeover (ATO)",
    descZh: "关联钓鱼凭据泄露、异常异地登录 (Impossible Travel) 与 IAM 访问密钥持久化滥用",
    descEn:
      "Correlates credential theft, impossible travel logins, and unauthorized IAM key creation",
    categoryZh: "账号安全",
    categoryEn: "Account Takeover",
  },
  "rule-web-attack-surge": {
    nameZh: "Web 应用漏洞利用突增聚簇",
    nameEn: "Web Application Exploit Surge",
    descZh: "关联同一攻击者实施的 SQL 注入、Log4Shell 及自动化端口嗅探组合攻击",
    descEn: "Correlates SQL injection, Log4Shell attempts, and reconnaissance against web assets",
    categoryZh: "漏洞利用",
    categoryEn: "Web Exploit",
  },
  "rule-critical-vuln-exposure": {
    nameZh: "边界暴露面高危在野漏洞关联",
    nameEn: "Critical Vulnerability Exposure & Exploitation",
    descZh: "关联堡垒机、VPN 网关及 K8s 节点暴露的 Citrix Bleed、runc 等高危在野漏洞",
    descEn:
      "Correlates actively exploited vulnerabilities on boundary VPNs, bastions, and K8s nodes",
    categoryZh: "脆弱性暴露",
    categoryEn: "Vulnerability Exposure",
  },
  "rule-bruteforce-cluster": {
    nameZh: "分布式多源 SSH 暴力破解集群",
    nameEn: "Distributed Multi-Source SSH Brute Force Cluster",
    descZh: "聚合多独立来源针对堡垒机与 VPN 的高频多波次凭据暴力破解行为",
    descEn:
      "Aggregates multi-source coordinated brute force attempts against bastions and VPN gateways",
    categoryZh: "凭据破解",
    categoryEn: "Brute Force",
  },
  "rule-scan-noise": {
    nameZh: "全网扫描噪音与背景无效探测过滤",
    nameEn: "Internet Scanning Noise & Background Reconnaissance",
    descZh: "聚合互联网背景低危端口探测与无效认证，沉淀降噪视图",
    descEn:
      "Aggregates benign internet background scanning and ineffective probing for noise reduction",
    categoryZh: "噪音过滤",
    categoryEn: "Reconnaissance Noise",
  },
  "rule-data-exfiltration": {
    nameZh: "多通道数据外发与异常流量外泄",
    nameEn: "Multi-Channel Data Exfiltration & Abnormal Outbound Traffic",
    descZh: "关联个人网盘上传、内部邮箱自动转发规则以及高危 DNS 隧道窃密活动",
    descEn:
      "Correlates personal cloud storage uploads, email forwarding rules, and covert DNS tunnels",
    categoryZh: "数据安全",
    categoryEn: "Data Exfiltration",
  },
  "rule-crypto-mining": {
    nameZh: "主机与容器异常算力消耗及挖矿木马",
    nameEn: "Host & Container Cryptomining / Resource Hijacking",
    descZh: "关联矿池网络通信、异常 CPU 峰值进程与系统定时任务持久化行为",
    descEn:
      "Correlates mining pool network traffic, abnormal CPU usage, and malicious cron persistence",
    categoryZh: "挖矿劫持",
    categoryEn: "Cryptomining",
  },
  "rule-ransomware-chain": {
    nameZh: "端点勒索软件全链路攻击链检测",
    nameEn: "End-to-End Ransomware Kill-Chain Detection",
    descZh: "聚合 C2 外连、LSASS 凭据窃取、新增后门管理员、横向移动与批量文件加密",
    descEn:
      "Correlates C2 beacons, credential dumping, rogue admin creation, lateral movement, and FIM encryption",
    categoryZh: "勒索攻击",
    categoryEn: "Ransomware",
  },
};

/**
 * Get localized rule information based on locale
 */
export function getLocalizedRule(
  rule: { id: string; name: string; description: string | null },
  locale: string
): {
  displayName: string;
  displayDescription: string;
  displayCategory: string;
  isCustom: boolean;
} {
  const isZh = locale.startsWith("zh");
  const idKey = rule.id?.trim().toLowerCase();
  const nameKey = rule.name?.trim().toLowerCase();

  // 1. Try finding by ID first
  let entry = CORRELATION_RULES_I18N[idKey];

  // 2. Try finding by exact name or name without demo prefix
  if (!entry && nameKey) {
    entry = CORRELATION_RULES_I18N[nameKey];

    // If demo rule name like "Demo Correlation Rule (rule-xxx)"
    if (!entry && nameKey.includes("demo correlation rule")) {
      const match = nameKey.match(/rule-[a-z0-9-]+/);
      if (match && CORRELATION_RULES_I18N[match[0]]) {
        entry = CORRELATION_RULES_I18N[match[0]];
      }
    }
  }

  if (entry) {
    return {
      displayName: isZh ? entry.nameZh : entry.nameEn,
      displayDescription: isZh ? entry.descZh : entry.descEn || rule.description || "",
      displayCategory: isZh ? entry.categoryZh : entry.categoryEn,
      isCustom: false,
    };
  }

  // Fallback for custom user-created rules
  return {
    displayName: rule.name,
    displayDescription: rule.description || "",
    displayCategory: isZh ? "自定义规则" : "Custom Rule",
    isCustom: true,
  };
}

/**
 * Helper to check if a rule matches the search query across all languages and fields
 */
export function matchesRuleSearch(
  rule: { id: string; name: string; description: string | null },
  query: string,
  locale: string
): boolean {
  if (!query || !query.trim()) return true;
  const q = query.trim().toLowerCase();

  // Check ID and raw name/desc
  if (rule.id?.toLowerCase().includes(q)) return true;
  if (rule.name?.toLowerCase().includes(q)) return true;
  if (rule.description?.toLowerCase().includes(q)) return true;

  // Check localized fields
  const localized = getLocalizedRule(rule, locale);
  if (localized.displayName.toLowerCase().includes(q)) return true;
  if (localized.displayDescription.toLowerCase().includes(q)) return true;
  if (localized.displayCategory.toLowerCase().includes(q)) return true;

  // Also check opposite language if defined in dictionary
  const idKey = rule.id?.trim().toLowerCase();
  const nameKey = rule.name?.trim().toLowerCase();
  let entry = CORRELATION_RULES_I18N[idKey] || CORRELATION_RULES_I18N[nameKey];
  if (!entry && nameKey?.includes("demo correlation rule")) {
    const match = nameKey.match(/rule-[a-z0-9-]+/);
    if (match) entry = CORRELATION_RULES_I18N[match[0]];
  }

  if (entry) {
    if (entry.nameZh.toLowerCase().includes(q)) return true;
    if (entry.nameEn.toLowerCase().includes(q)) return true;
    if (entry.descZh.toLowerCase().includes(q)) return true;
    if (entry.descEn.toLowerCase().includes(q)) return true;
    if (entry.categoryZh.toLowerCase().includes(q)) return true;
    if (entry.categoryEn.toLowerCase().includes(q)) return true;
  }

  return false;
}
