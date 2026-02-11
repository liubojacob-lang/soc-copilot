"""Playbook engine for generating SIEM queries and remediation actions."""

import re
import uuid
from typing import Any
from .query_templates import (
    get_queries_for_platform,
    format_time_range,
    SPLUNK_QUERIES,
    ELASTIC_KQL_QUERIES,
    SENTINEL_KQL_QUERIES,
)


def generate_siem_queries(
    iocs: dict[str, list[str]],
    platforms: list[str],
    time_ranges: list[str],
) -> list[dict[str, Any]]:
    """Generate SIEM queries for multiple platforms.

    Args:
        iocs: Dict with keys 'ips', 'domains', 'urls', 'hashes'
        platforms: List of platforms ['splunk', 'elastic_kql', 'sentinel_kql']
        time_ranges: List of time ranges ['last_1h', 'last_24h', 'last_7d']

    Returns:
        List of platform queries with formatted queries
    """
    results = []

    for platform in platforms:
        if platform not in ["splunk", "elastic_kql", "sentinel_kql"]:
            continue

        platform_queries = get_queries_for_platform(platform)
        queries = []

        for time_range in time_ranges:
            time_range_str = format_time_range(platform, time_range)

            for query_key, query_template in platform_queries.items():
                formatted_query = _format_query_template(
                    query_template["query_template"],
                    platform,
                    time_range_str,
                    time_range,
                    iocs,
                )

                queries.append({
                    "name": query_template["name"],
                    "description": query_template["description"],
                    "query": formatted_query,
                    "time_range": time_range,
                    "fields_expected": query_template["fields_expected"],
                    "prerequisite": query_template["prerequisite"],
                })

        results.append({
            "platform": platform,
            "queries": queries,
        })

    return results


def _format_query_template(
    template: str,
    platform: str,
    time_range_str: str,
    time_range_key: str,
    iocs: dict[str, list[str]],
) -> str:
    """Format a query template with actual IOC values.

    Args:
        template: Query template string
        platform: Platform name
        time_range_str: Formatted time range
        time_range_key: Time range key for Sentinel (1h, 24h, 7d)
        iocs: Dict of IOCs

    Returns:
        Formatted query string
    """
    query = template

    # Replace time range
    query = query.replace("{time_range}", time_range_str)

    # For Sentinel, also replace time_value
    if platform == "sentinel_kql":
        time_value_map = {"last_1h": "1h", "last_24h": "24h", "last_7d": "7d"}
        query = query.replace("{time_value}", time_value_map.get(time_range_key, "24h"))

    # Replace IP IOCs
    ips = iocs.get("ips", [])[:10]
    if "{ioc_ips}" in query:
        if ips:
            if platform == "splunk":
                ips_str = ", ".join([f'"{ip}"' for ip in ips])
            else:
                ips_str = ", ".join([f'"{ip}"' for ip in ips])
            query = query.replace("{ioc_ips}", ips_str)
        else:
            query = query.replace("{ioc_ips}", '"NO_IPS_PROVIDED"')

    # Replace domain IOCs
    domains = iocs.get("domains", [])[:10]
    if "{ioc_domains}" in query:
        if domains:
            domains_str = ", ".join([f'"{d}"' for d in domains])
            query = query.replace("{ioc_domains}", domains_str)
        else:
            query = query.replace("{ioc_domains}", '"NO_DOMAINS_PROVIDED"')

    # Replace URL IOCs
    urls = iocs.get("urls", [])
    if "{ioc_url_pattern}" in query or "{ioc_urls}" in query:
        if urls:
            # Extract domain from URLs for pattern matching
            url_patterns = []
            for url in urls[:5]:
                match = re.search(r"https?://([^/]+)", url)
                if match:
                    url_patterns.append(match.group(1))
            if url_patterns:
                if platform == "splunk":
                    patterns_str = "|".join(url_patterns)
                else:
                    patterns_str = ", ".join([f'"{p}"' for p in url_patterns])
                query = query.replace("{ioc_url_pattern}", patterns_str)
                query = query.replace("{ioc_urls}", patterns_str)
            else:
                query = query.replace("{ioc_url_pattern}", "example.com")
                query = query.replace("{ioc_urls}", '"example.com"')
        else:
            query = query.replace("{ioc_url_pattern}", "example.com")
            query = query.replace("{ioc_urls}", '"example.com"')

    # Replace hash IOCs
    hashes = iocs.get("hashes", [])
    if "{ioc_hashes}" in query:
        if hashes:
            hashes_str = ", ".join([f'"{h}"' for h in hashes[:10]])
            query = query.replace("{ioc_hashes}", hashes_str)
        else:
            query = query.replace("{ioc_hashes}", '"NO_HASHES_PROVIDED"')

    return query


def generate_remediation_actions(
    iocs: dict[str, list[str]],
    primary_asset: dict[str, Any] | None,
    impact_analysis: dict[str, Any] | None,
    threat_intel: dict[str, Any] | None,
    policy: str = "safe",
) -> list[dict[str, Any]]:
    """Generate remediation actions based on analysis.

    Args:
        iocs: Dict of IOCs
        primary_asset: Primary affected asset info
        impact_analysis: Impact analysis results
        threat_intel: Threat intelligence results
        policy: Policy level (safe, moderate, aggressive)

    Returns:
        List of remediation action dictionaries
    """
    actions = []
    priority = 1

    # Get malicious IOCs from threat intel
    malicious_iocs = _get_malicious_iocs(threat_intel)

    # Get affected assets
    affected_assets = impact_analysis.get("affected_assets", []) if impact_analysis else []

    # Action 1: Block outbound traffic to malicious IPs (highest priority)
    if malicious_iocs.get("ips"):
        actions.append({
            "title": "Block outbound traffic to malicious IP addresses",
            "risk": _get_risk_level(primary_asset, "high" if malicious_iocs["ips"] else "medium"),
            "category": "containment",
            "priority": priority,
            "steps": [
                {
                    "action": "Block malicious IPs at network perimeter",
                    "method": "Firewall rule / Network Security Group",
                    "command": _generate_firewall_block_cmd(malicious_iocs["ips"][:5]),
                },
                {
                    "action": "Update host-based firewall rules",
                    "method": "Windows Firewall / iptables",
                    "command": _generate_host_firewall_cmd(malicious_iocs["ips"][:5]),
                },
            ],
            "verification": [
                "Verify blocked IPs cannot be reached from internal network",
                "Check firewall logs for block attempts",
                "Run telnet/nc test to blocked IPs from affected hosts",
            ],
            "rollback": [
                "Document firewall rule with timestamp and incident reference",
                "Set automatic expiration for temporary blocks (e.g., 30 days)",
                "Rollback: Remove firewall rule after threat period ends",
            ],
            "rationale": f"Preventing outbound communication to {len(malicious_iocs['ips'])} confirmed malicious IP addresses",
        })
        priority += 1

    # Action 2: Isolate affected assets
    if affected_assets:
        critical_assets = [a for a in affected_assets if a.get("criticality") in ["critical", "high"]]
        if critical_assets:
            actions.append({
                "title": "Isolate critical affected assets from network",
                "risk": "high",
                "category": "containment",
                "priority": priority,
                "steps": [
                    {
                        "action": "Network isolation of affected hosts",
                        "method": "VLAN isolation / Port shutdown",
                        "command": _generate_isolation_cmd([a.get("hostname") or a.get("ip") for a in critical_assets[:3]]),
                    },
                    {
                        "action": "Disable network adapters on compromised hosts",
                        "method": "OS-level network disable",
                        "command": "# Windows: Disable-NetAdapter -Name \"Ethernet\"\n# Linux: ifconfig eth0 down",
                    },
                ],
                "verification": [
                    "Confirm isolated host cannot communicate with network",
                    "Verify ping tests fail to isolated host",
                    "Check that critical services on host are stopped or redirected",
                ],
                "rollback": [
                    "Document isolation reason and timestamp",
                    "Re-enable network adapter only after forensic acquisition",
                    "Rollback: Re-enable network port/adapters post-incident",
                ],
                "rationale": f"Isolating {len(critical_assets)} critical/high-risk assets to prevent lateral movement",
            })
            priority += 1

    # Action 3: Block malicious domains via DNS
    if malicious_iocs.get("domains"):
        actions.append({
            "title": "Block malicious domains via DNS sinkhole",
            "risk": "medium",
            "category": "containment",
            "priority": priority,
            "steps": [
                {
                    "action": "Add DNS blocklist entries",
                    "method": "DNS server / DNS sinkhole",
                    "command": _generate_dns_block_cmd(malicious_iocs["domains"][:10]),
                },
                {
                    "action": "Clear DNS cache on affected systems",
                    "method": "ipconfig / flushdns or systemd-resolve --flush-caches",
                    "command": "# Windows: ipconfig /flushdns\n# Linux: systemd-resolve --flush-caches",
                },
            ],
            "verification": [
                "Test DNS resolution for blocked domains returns sinkhole IP",
                "Check DNS query logs show NXDOMAIN or sinkhole response",
                "Verify no successful connections to blocked domains after implementation",
            ],
            "rollback": [
                "Document DNS block entries with incident reference",
                "Set expiration date for temporary blocks",
                "Rollback: Remove DNS sinkhole entries after threat period",
            ],
            "rationale": f"Preventing DNS resolution of {len(malicious_iocs['domains'])} malicious domains to block C2/Phishing",
        })
        priority += 1

    # Action 4: Kill malicious processes
    if iocs.get("hashes") and policy in ["moderate", "aggressive"]:
        actions.append({
            "title": "Terminate processes matching malicious file hashes",
            "risk": "medium",
            "category": "eradication",
            "priority": priority,
            "steps": [
                {
                    "action": "Identify running processes with malicious hashes",
                    "method": "Process enumeration / EDR",
                    "command": _generate_process_kill_cmd(iocs["hashes"][:5]),
                },
                {
                    "action": "Quarantine malicious files",
                    "method": "Antivirus / EDR quarantine",
                    "command": "# Use EDR console to quarantine files by hash",
                },
            ],
            "verification": [
                "Verify processes are no longer running",
                "Confirm quarantined files cannot be executed",
                "Check EDR alerts for execution attempts post-termination",
            ],
            "rollback": [
                "Maintain forensic copy of quarantined files",
                "Document process termination details for investigation",
                "Rollback: Restore from quarantine only for false positives (approval required)",
            ],
            "rationale": f"Terminating processes matching {len(iocs['hashes'])} suspicious file hashes",
        })
        priority += 1

    # Action 5: Scan for artifacts related to IOCs
    actions.append({
        "title": "Perform full artifact scan for related IOCs",
        "risk": "low",
        "category": "eradication",
        "priority": priority,
        "steps": [
            {
                "action": "Scan filesystem for malicious file hashes",
                "method": "Forensic scanner / EDR full scan",
                "command": _generate_scan_cmd(iocs.get("hashes", [])[:5]),
            },
            {
                "action": "Search registry/artifacts for IOC references",
                "method": "Registry search / Artifact hunt",
                "command": '# Windows: reg query HKLM\\SOFTWARE /s /f "IOC_PATTERN"\n# Linux: grep -r "IOC_PATTERN" /etc /var',
            },
        ],
        "verification": [
            "Review scan results for additional infected files",
            "Cross-reference findings with IOC list",
            "Document all discovered artifacts for investigation",
        ],
        "rollback": [
            "No rollback needed - read-only scan operation",
        ],
        "rationale": "Comprehensive scan to identify all artifacts related to confirmed IOCs",
    })
    priority += 1

    # Action 6: Credential reset for affected accounts
    if iocs.get("ips") or affected_assets:
        actions.append({
            "title": "Force password reset for potentially compromised accounts",
            "risk": "low",
            "category": "recovery",
            "priority": priority,
            "steps": [
                {
                    "action": "Identify accounts that logged in from malicious IPs or affected assets",
                    "method": "Log analysis / Identity provider logs",
                    "command": "# Query authentication logs for logins from IOC IPs\n# Example: select * from sign-in logs where IPAddress in (IOC_IPs)",
                },
                {
                    "action": "Force password reset for identified accounts",
                    "method": "Identity management / AD reset",
                    "command": "# Azure AD: Connect-AzureAD | Set-AzureADUserPassword\n# AD: Set-ADAccountPassword -Identity <user> -Reset",
                },
                {
                    "action": "Revoke all active sessions",
                    "method": "Identity management / session termination",
                    "command": "# Azure AD: Revoke-AzureADUserAllRefreshToken\n# AD: Disable-ADAccount -Identity <user>; Enable-ADAccount -Identity <user>",
                },
            ],
            "verification": [
                "Confirm users must create new password at next login",
                "Verify old credentials no longer work",
                "Check for successful authentication after reset using new credentials only",
            ],
            "rollback": [
                "No rollback needed - security best practice for potentially compromised accounts",
            ],
            "rationale": "Preventing further unauthorized access using potentially compromised credentials",
        })
        priority += 1

    # Action 7: Enable enhanced monitoring
    actions.append({
        "title": "Enable enhanced monitoring for affected assets",
        "risk": "low",
        "category": "recovery",
        "priority": priority,
        "steps": [
            {
                "action": "Enable comprehensive audit logging",
                "method": "Group Policy / audit configuration",
                "command": "# Enable all audit policies via Group Policy\n# auditpol /set /subcategory:* /success:enable /failure:enable",
            },
            {
                "action": "Add EDR/alerting rules for IOC patterns",
                "method": "SIEM alert rules / EDR watchlists",
                "command": "# Create SIEM alert for IOC re-appearance\n# Add EDR watchlist for IOC hashes/domains",
            },
        ],
        "verification": [
            "Confirm enhanced logs are being collected",
            "Test alert rule triggers on IOC pattern match",
            "Verify log retention policy covers incident period",
        ],
        "rollback": [
            "Document monitoring changes with incident reference",
            "Review and adjust monitoring levels post-incident",
            "Rollback: Remove temporary alert rules after threat period expires",
        ],
        "rationale": "Enhancing detection capability to identify recurrence or related activity",
    })

    # Sort by priority
    actions.sort(key=lambda x: x["priority"])

    return actions


def _get_malicious_iocs(threat_intel: dict[str, Any] | None) -> dict[str, list[str]]:
    """Extract malicious IOCs from threat intel results."""
    if not threat_intel:
        return {"ips": [], "domains": [], "urls": [], "hashes": []}

    malicious = {"ips": [], "domains": [], "urls": [], "hashes": []}

    for item in threat_intel.get("items", []):
        if item.get("verdict") in ["malicious", "suspicious"]:
            ioc_type = item.get("ioc_type", "")
            ioc_value = item.get("ioc_value", "")
            if ioc_type == "ip":
                malicious["ips"].append(ioc_value)
            elif ioc_type == "domain":
                malicious["domains"].append(ioc_value)
            elif ioc_type == "url":
                malicious["urls"].append(ioc_value)
            elif ioc_type == "hash":
                malicious["hashes"].append(ioc_value)

    return malicious


def _get_risk_level(asset: dict[str, Any] | None, default: str = "medium") -> str:
    """Determine risk level based on asset criticality."""
    if not asset:
        return default

    criticality = asset.get("criticality", "medium")
    risk_map = {
        "critical": "critical",
        "high": "high",
        "medium": "medium",
        "low": "low",
    }
    return risk_map.get(criticality, default)


def _generate_firewall_block_cmd(ips: list[str]) -> str:
    """Generate firewall block command."""
    if not ips:
        return "# No IPs to block"

    cmds = []
    for ip in ips[:5]:
        cmds.append(f"# Block {ip}")
        cmds.append(f"firewall-cmd --permanent --add-rich-rule='rule family=ipv4 destination address={ip} reject'")
        cmds.append(f"iptables -A INPUT -s {ip} -j DROP")
        cmds.append(f"ip route add blackhole {ip}")

    return "\n".join(cmds)


def _generate_host_firewall_cmd(ips: list[str]) -> str:
    """Generate host-based firewall command."""
    if not ips:
        return "# No IPs to block"

    cmds = []
    for ip in ips[:5]:
        cmds.append(f"# Windows: New-NetFirewallRule -DisplayName 'Block {ip}' -Direction Outbound -RemoteAddress {ip} -Action Block")
        cmds.append(f"# Linux: iptables -A OUTPUT -d {ip} -j DROP")

    return "\n".join(cmds)


def _generate_isolation_cmd(hosts: list[str]) -> str:
    """Generate isolation command for hosts."""
    if not hosts:
        return "# No hosts to isolate"

    cmds = []
    for host in hosts[:3]:
        cmds.append(f"# Isolate host: {host}")
        cmds.append(f"# Switch: shutdown interface / VLAN isolate")
        cmds.append(f"# Network: revoke IP address from DHCP")

    return "\n".join(cmds)


def _generate_dns_block_cmd(domains: list[str]) -> str:
    """Generate DNS block command."""
    if not domains:
        return "# No domains to block"

    cmds = []
    cmds.append("# Add to DNS blocklist (BIND/Unbound/Windows DNS)")
    for domain in domains[:10]:
        cmds.append(f'zone "{domain}" {{ type master; file "blocked.zone"; };')
        cmds.append(f"# Or use RPZ: {domain} CNAME .")

    return "\n".join(cmds)


def _generate_process_kill_cmd(hashes: list[str]) -> str:
    """Generate process kill command."""
    if not hashes:
        return "# No hashes to search"

    cmds = []
    cmds.append("# Find and terminate processes by hash")
    cmds.append("# Windows:")
    for h in hashes[:5]:
        cmds.append(f"Get-Process | Where-Object {{ (Get-FileHash $_.Path -Algorithm SHA256).Hash -eq '{h}' }} | Stop-Process -Force")

    cmds.append("# Linux:")
    cmds.append("for hash in HASH1 HASH2 HASH3; do")
    cmds.append("  pid=$(lsof / | awk '{print $1}' | sort -u | xargs -I{} sha256sum /proc/{}/exe 2>/dev/null | grep '$hash' | cut -d' ' -f3)")
    cmds.append("  kill -9 $pid")
    cmds.append("done")

    return "\n".join(cmds)


def _generate_scan_cmd(hashes: list[str]) -> str:
    """Generate scan command."""
    if not hashes:
        return "# No hashes to scan"

    cmds = []
    cmds.append("# Full filesystem scan for malicious hashes")
    cmds.append("# Windows:")
    for h in hashes[:5]:
        cmds.append(f"Get-ChildItem -Path C:\\ -Recurse -ErrorAction SilentlyContinue | Where-Object {{ (Get-FileHash $_.FullName -Algorithm SHA256).Hash -eq '{h}' }}")

    cmds.append("# Linux:")
    cmds.append("find / -type f -exec sha256sum {} \\; | grep -E '{}'".format("|".join(hashes[:5])))

    return "\n".join(cmds)
