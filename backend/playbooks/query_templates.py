"""SIEM query templates for Splunk, Elastic KQL, and Microsoft Sentinel KQL."""

from typing import Final

# Time range mappings
TIME_RANGE_MAP: Final[dict[str, dict[str, str]]] = {
    "splunk": {
        "last_1h": "earliest=-1h latest=now",
        "last_24h": "earliest=-24h latest=now",
        "last_7d": "earliest=-7d latest=now",
    },
    "elastic_kql": {
        "last_1h": "@timestamp >= now-1h",
        "last_24h": "@timestamp >= now-24h",
        "last_7d": "@timestamp >= now-7d",
    },
    "sentinel_kql": {
        "last_1h": "where TimeGenerated > ago(1h)",
        "last_24h": "where TimeGenerated > ago(24h)",
        "last_7d": "where TimeGenerated > ago(7d)",
    },
}


def format_time_range(platform: str, time_range: str) -> str:
    """Get formatted time range for platform."""
    return TIME_RANGE_MAP.get(platform, {}).get(time_range, "")


# Common field names for different log sources
FIELD_ALIASES: Final[dict[str, dict[str, list[str]]]] = {
    "dest_ip": ["dest_ip", "dst_ip", "destination_ip", "DestinationIp", "d_ip"],
    "src_ip": ["src_ip", "source_ip", "SourceIp", "s_ip", "ip_address"],
    "dest_port": ["dest_port", "dst_port", "destination_port", "DestinationPort", "dport"],
    "src_port": ["src_port", "source_port", "SourcePort", "sport"],
    "hostname": ["hostname", "host", "computer_name", "Computer", "dest_host"],
    "user": ["user", "username", "User", "user_name", "account"],
    "domain": ["domain", "dns_query", "query_name", "query"],
    "url": ["url", "request_url", "uri", "full_url"],
    "hash": ["hash", "file_hash", "md5", "sha256", "sha1"],
    "process_name": ["process_name", "process", "process_name_string", "Image"],
    "file_name": ["file_name", "filename", "target_filename", "FileName"],
}


def get_field_expr(platform: str, field: str, alias_index: int = 0) -> str:
    """Get field expression for platform with optional alias."""
    aliases = FIELD_ALIASES.get(field, [field])
    selected_alias = aliases[alias_index % len(aliases)]

    if platform == "splunk":
        return selected_alias
    elif platform == "elastic_kql":
        return selected_alias
    elif platform == "sentinel_kql":
        # Sentinel uses PascalCase typically
        return selected_alias
    return selected_alias


# ============================================================================
# SPLUNK QUERY TEMPLATES
# ============================================================================

SPLUNK_QUERIES: Final[dict[str, dict]] = {
    "outbound_to_ioc_ip": {
        "name": "Outbound connections to IOC IP",
        "description": "Find internal hosts connecting to suspicious external IP addresses",
        "query_template": "index=firewall OR index=proxy {time_range} action=allowed | where dest_ip in ({ioc_ips}) | stats count by src_ip, dest_ip, dest_port, user | sort - count",
        "time_range": "last_24h",
        "fields_expected": ["src_ip", "dest_ip", "dest_port", "user", "count"],
        "prerequisite": "Requires firewall or proxy logs with network traffic"
    },
    "dns_query_ioc_domain": {
        "name": "DNS queries for IOC domain",
        "description": "Detect DNS queries to known malicious domains",
        "query_template": "index=dns {time_range} | where domain in ({ioc_domains}) | stats count by host, domain, response_code | sort - count",
        "time_range": "last_24h",
        "fields_expected": ["host", "domain", "response_code", "count"],
        "prerequisite": "Requires DNS logs"
    },
    "web_access_ioc_url": {
        "name": "Web access to IOC URL",
        "description": "Find HTTP/HTTPS requests to suspicious URLs",
        "query_template": "index=proxy OR index=web {time_range} | where match(url, \"({ioc_url_pattern})\") | stats count by src_ip, url, user_agent | sort - count",
        "time_range": "last_24h",
        "fields_expected": ["src_ip", "url", "user_agent", "count"],
        "prerequisite": "Requires proxy or web server logs"
    },
    "suspicious_process_execution": {
        "name": "Suspicious process execution",
        "description": "Detect execution of suspicious processes (PowerShell, cmd with encoded commands)",
        "query_template": "index=sysmon {time_range} EventCode=1 | where match(process_name, \"(?i)(powershell|pwsh|cmd|cscript|wscript)\") | where match(command_line, \"(?i)(-enc|-encoded|-e |downloadstring|iex|invoke-expression)\") | stats count by host, process_name, command_line | sort - count",
        "time_range": "last_24h",
        "fields_expected": ["host", "process_name", "command_line", "count"],
        "prerequisite": "Requires Sysmon Event ID 1 (Process Create)"
    },
    "login_failure_bruteforce": {
        "name": "Login failure (brute force detection)",
        "description": "Detect multiple failed login attempts from same source",
        "query_template": "index=winlog {time_range} EventCode=4625 | stats count as failures by src_ip, user, host | where failures >= 5 | sort - failures",
        "time_range": "last_24h",
        "fields_expected": ["src_ip", "user", "host", "failures"],
        "prerequisite": "Requires Windows Event Log 4625 (Login Failure)"
    },
    "lateral_movement_rdp": {
        "name": "Lateral movement via RDP",
        "description": "Detect RDP connections between internal hosts",
        "query_template": "index=firewall OR index=sysmon {time_range} action=allowed dest_port=3389 | where NOT match(dest_ip, \"10\\.0\\.0\\.0/8|192\\.168\\.0\\.0/16|172\\.16\\.0\\.0/12\") OR (match(dest_ip, \"10\\.0\\.0\\.0/8|192\\.168\\.0\\.0/16|172\\.16\\.0\\.0/12\") AND match(src_ip, \"10\\.0\\.0\\.0/8|192\\.168\\.0\\.0/16|172\\.16\\.0\\.0/12\")) | stats count by src_ip, dest_ip, user | sort - count",
        "time_range": "last_24h",
        "fields_expected": ["src_ip", "dest_ip", "user", "count"],
        "prerequisite": "Requires firewall or Sysmon network connection logs"
    },
    "lateral_movement_smb": {
        "name": "Lateral movement via SMB",
        "description": "Detect SMB connections between internal hosts (potential SMB exploitation)",
        "query_template": "index=sysmon {time_range} EventCode=3 dest_port in (139, 445) | stats count by src_ip, dest_ip, user | sort - count",
        "time_range": "last_24h",
        "fields_expected": ["src_ip", "dest_ip", "user", "count"],
        "prerequisite": "Requires Sysmon Event ID 3 (Network Connect)"
    },
    "file_drop_by_hash": {
        "name": "File drop by IOC hash",
        "description": "Find files with known malicious hashes",
        "query_template": "index=sysmon {time_range} EventCode=6 | where hash in ({ioc_hashes}) | stats count by host, file_name, hash | sort - count",
        "time_range": "last_7d",
        "fields_expected": ["host", "file_name", "hash", "count"],
        "prerequisite": "Requires Sysmon Event ID 6 (File Create) with hash calculation"
    },
    "host_anomaly_aggregation": {
        "name": "Host anomaly aggregation (multi-signal)",
        "description": "Find hosts with multiple suspicious activities within 1 hour",
        "query_template": "index=sysmon {time_range} (EventCode=1 OR EventCode=3 OR EventCode=6) | bin _time span=1h | stats count BY host, EventCode | where count > 10 | eval risk_score = case(EventCode=1, 2, EventCode=3, 1, EventCode=6, 3) | stats sum(risk_score) as total_risk by host | sort - total_risk",
        "time_range": "last_1h",
        "fields_expected": ["host", "total_risk", "EventCode"],
        "prerequisite": "Requires Sysmon logs with multiple event types"
    },
    "privilege_escalation": {
        "name": "Privilege escalation attempts",
        "description": "Detect processes requesting privileges or running as SYSTEM",
        "query_template": "index=sysmon {time_range} EventCode=1 | where match(command_line, \"(?i)(-privileges|admin|system|sudo|runas)\") OR user_name=\"*SYSTEM\" | stats count by host, process_name, user_name | sort - count",
        "time_range": "last_24h",
        "fields_expected": ["host", "process_name", "user_name", "count"],
        "prerequisite": "Requires Sysmon Event ID 1 (Process Create)"
    },
    "new_service_creation": {
        "name": "New service creation",
        "description": "Detect creation of new Windows services (persistence mechanism)",
        "query_template": "index=sysmon {time_range} EventCode=6 | where match(file_name, \"(?i)(\\\\svchost\\.exe|\\\\services\\.exe)\") OR match(command_line, \"(?i)(sc create|net start|New-Service)\") | stats count by host, file_name, command_line | sort - count",
        "time_range": "last_24h",
        "fields_expected": ["host", "file_name", "command_line", "count"],
        "prerequisite": "Requires Sysmon Event ID 6 (File Create)"
    },
    "scheduled_task_creation": {
        "name": "Scheduled task creation",
        "description": "Detect creation of scheduled tasks (persistence mechanism)",
        "query_template": "index=sysmon {time_range} EventCode=1 | where match(process_name, \"(?i)schtasks\\.exe\") AND match(command_line, \"(?i)(/create|/sc)\") | stats count by host, command_line | sort - count",
        "time_range": "last_24h",
        "fields_expected": ["host", "command_line", "count"],
        "prerequisite": "Requires Sysmon Event ID 1 (Process Create)"
    },
}


# ============================================================================
# ELASTIC KQL QUERY TEMPLATES
# ============================================================================

ELASTIC_KQL_QUERIES: Final[dict[str, dict]] = {
    "outbound_to_ioc_ip": {
        "name": "Outbound connections to IOC IP",
        "description": "Find internal hosts connecting to suspicious external IP addresses",
        "query_template": "{time_range} AND (event.dataset:\"firewall\" OR event.dataset:\"proxy\") AND action:\"allowed\" AND destination_ip:(\"{ioc_ips}\") | stats count=connections by source_ip, destination_ip, destination_port, user.name | sort connections: desc",
        "time_range": "last_24h",
        "fields_expected": ["source_ip", "destination_ip", "destination_port", "user.name", "connections"],
        "prerequisite": "Requires firewall or proxy logs with network traffic"
    },
    "dns_query_ioc_domain": {
        "name": "DNS queries for IOC domain",
        "description": "Detect DNS queries to known malicious domains",
        "query_template": "{time_range} AND event.dataset:\"dns\" AND dns.query.name:(\"{ioc_domains}\") | stats count=queries by host.hostname, dns.query.name, dns.response_code | sort queries: desc",
        "time_range": "last_24h",
        "fields_expected": ["host.hostname", "dns.query.name", "dns.response_code", "queries"],
        "prerequisite": "Requires DNS logs"
    },
    "web_access_ioc_url": {
        "name": "Web access to IOC URL",
        "description": "Find HTTP/HTTPS requests to suspicious URLs",
        "query_template": "{time_range} AND (event.dataset:\"proxy\" OR event.dataset:\"web\") AND url.original: *{ioc_url_pattern}* | stats count=requests by source_ip, url.original, user_agent.original | sort requests: desc",
        "time_range": "last_24h",
        "fields_expected": ["source_ip", "url.original", "user_agent.original", "requests"],
        "prerequisite": "Requires proxy or web server logs"
    },
    "suspicious_process_execution": {
        "name": "Suspicious process execution",
        "description": "Detect execution of suspicious processes (PowerShell, cmd with encoded commands)",
        "query_template": "{time_range} AND event.code:\"1\" AND process.name:(*powershell* OR *pwsh* OR *cmd.exe OR *cscript.exe* OR *wscript.exe*) AND process.command_line:(*-enc* OR *-encoded* OR *-e * OR *downloadstring* OR *iex* OR *invoke-expression*) | stats count=executions by host.hostname, process.name, process.command_line | sort executions: desc",
        "time_range": "last_24h",
        "fields_expected": ["host.hostname", "process.name", "process.command_line", "executions"],
        "prerequisite": "Requires Sysmon Event ID 1 (Process Create)"
    },
    "login_failure_bruteforce": {
        "name": "Login failure (brute force detection)",
        "description": "Detect multiple failed login attempts from same source",
        "query_template": "{time_range} AND winlog.event_id:\"4625\" | stats count=failures by winlog.computer_name, source.ip, user.name | filter failures >= 5 | sort failures: desc",
        "time_range": "last_24h",
        "fields_expected": ["winlog.computer_name", "source.ip", "user.name", "failures"],
        "prerequisite": "Requires Windows Event Log 4625 (Login Failure)"
    },
    "lateral_movement_rdp": {
        "name": "Lateral movement via RDP",
        "description": "Detect RDP connections between internal hosts",
        "query_template": "{time_range} AND event.code:\"3\" AND destination.port:3389 | stats count=connections by source.ip, destination.ip, user.name | sort connections: desc",
        "time_range": "last_24h",
        "fields_expected": ["source.ip", "destination.ip", "user.name", "connections"],
        "prerequisite": "Requires Sysmon network connection logs"
    },
    "lateral_movement_smb": {
        "name": "Lateral movement via SMB",
        "description": "Detect SMB connections between internal hosts (potential SMB exploitation)",
        "query_template": "{time_range} AND event.code:\"3\" AND destination.port:(139 OR 445) | stats count=connections by source.ip, destination.ip, user.name | sort connections: desc",
        "time_range": "last_24h",
        "fields_expected": ["source.ip", "destination.ip", "user.name", "connections"],
        "prerequisite": "Requires Sysmon Event ID 3 (Network Connect)"
    },
    "file_drop_by_hash": {
        "name": "File drop by IOC hash",
        "description": "Find files with known malicious hashes",
        "query_template": "{time_range} AND event.code:\"6\" AND hash.imphash:(\"{ioc_hashes}\") | stats count=detections by host.hostname, file.name, hash.imphash | sort detections: desc",
        "time_range": "last_7d",
        "fields_expected": ["host.hostname", "file.name", "hash.imphash", "detections"],
        "prerequisite": "Requires Sysmon Event ID 6 (File Create) with hash calculation"
    },
    "host_anomaly_aggregation": {
        "name": "Host anomaly aggregation (multi-signal)",
        "description": "Find hosts with multiple suspicious activities within 1 hour",
        "query_template": "{time_range} AND event.provider:\"Microsoft-Windows-Sysmon\" AND event.code:(1 OR 3 OR 6) | stats count=sysmon_events by host.hostname, event.code | filter sysmon_events > 10 | eval risk_score = case(event.code == \"1\", 2, event.code == \"3\", 1, event.code == \"6\", 3) | stats sum(risk_score)=total_risk by host.hostname | sort total_risk: desc",
        "time_range": "last_1h",
        "fields_expected": ["host.hostname", "total_risk", "event.code"],
        "prerequisite": "Requires Sysmon logs with multiple event types"
    },
    "privilege_escalation": {
        "name": "Privilege escalation attempts",
        "description": "Detect processes requesting privileges or running as SYSTEM",
        "query_template": "{time_range} AND event.code:\"1\" AND (process.command_line:(*privileges* OR *admin* OR *system* OR *sudo* OR *runas*) OR user.name:*SYSTEM*) | stats count=attempts by host.hostname, process.name, user.name | sort attempts: desc",
        "time_range": "last_24h",
        "fields_expected": ["host.hostname", "process.name", "user.name", "attempts"],
        "prerequisite": "Requires Sysmon Event ID 1 (Process Create)"
    },
    "new_service_creation": {
        "name": "New service creation",
        "description": "Detect creation of new Windows services (persistence mechanism)",
        "query_template": "{time_range} AND event.code:\"6\" AND (file.name:(*svchost.exe* OR *services.exe*) OR process.command_line:(*sc create* OR *net start* OR *New-Service*)) | stats count=creations by host.hostname, file.name, process.command_line | sort creations: desc",
        "time_range": "last_24h",
        "fields_expected": ["host.hostname", "file.name", "process.command_line", "creations"],
        "prerequisite": "Requires Sysmon Event ID 6 (File Create)"
    },
    "scheduled_task_creation": {
        "name": "Scheduled task creation",
        "description": "Detect creation of scheduled tasks (persistence mechanism)",
        "query_template": "{time_range} AND event.code:\"1\" AND process.name:(*schtasks.exe*) AND process.command_line:(*create* OR *sc*) | stats count=creations by host.hostname, process.command_line | sort creations: desc",
        "time_range": "last_24h",
        "fields_expected": ["host.hostname", "process.command_line", "creations"],
        "prerequisite": "Requires Sysmon Event ID 1 (Process Create)"
    },
}


# ============================================================================
# SENTINEL KQL QUERY TEMPLATES
# ============================================================================

SENTINEL_KQL_QUERIES: Final[dict[str, dict]] = {
    "outbound_to_ioc_ip": {
        "name": "Outbound connections to IOC IP",
        "description": "Find internal hosts connecting to suspicious external IP addresses",
        "query_template": "let iocIps = dynamic({ioc_ips});\nDeviceNetworkEvents\n| where TimeGenerated > ago({time_value})\n| where ActionType == \"ConnectionAllowed\" and RemoteIP in (iocIps)\n| summarize Count=count() by DeviceName, RemoteIP, RemotePort, InitiatingProcessAccountName\n| sort by Count desc",
        "time_range": "last_24h",
        "fields_expected": ["DeviceName", "RemoteIP", "RemotePort", "InitiatingProcessAccountName", "Count"],
        "prerequisite": "Requires Microsoft Defender for Endpoint (DeviceNetworkEvents table)"
    },
    "dns_query_ioc_domain": {
        "name": "DNS queries for IOC domain",
        "description": "Detect DNS queries to known malicious domains",
        "query_template": "let iocDomains = dynamic({ioc_domains});\nDnsEvents\n| where TimeGenerated > ago({time_value})\n| where Name in (iocDomains)\n| summarize Count=count() by Computer, Name, ResponseCode\n| sort by Count desc",
        "time_range": "last_24h",
        "fields_expected": ["Computer", "Name", "ResponseCode", "Count"],
        "prerequisite": "Requires DNS logs (DnsEvents table)"
    },
    "web_access_ioc_url": {
        "name": "Web access to IOC URL",
        "description": "Find HTTP/HTTPS requests to suspicious URLs",
        "query_template": "let iocUrls = dynamic({ioc_urls});\nDeviceNetworkEvents\n| where TimeGenerated > ago({time_value})\n| where ActionType in (\"ConnectionAllowed\", \"NetworkConnectionConnected\")\n| where Url has_any (iocUrls)\n| summarize Count=count() by DeviceName, Url, InitiatingProcessAccountName\n| sort by Count desc",
        "time_range": "last_24h",
        "fields_expected": ["DeviceName", "Url", "InitiatingProcessAccountName", "Count"],
        "prerequisite": "Requires Microsoft Defender for Endpoint"
    },
    "suspicious_process_execution": {
        "name": "Suspicious process execution",
        "description": "Detect execution of suspicious processes (PowerShell, cmd with encoded commands)",
        "query_template": "DeviceProcessEvents\n| where TimeGenerated > ago({time_value})\n| where InitiatingProcessFileName in~ (\"powershell.exe\", \"pwsh.exe\", \"cmd.exe\", \"cscript.exe\", \"wscript.exe\")\n| where ProcessCommandLine has_any (\"-enc\", \"-encoded\", \"-e \", \"downloadstring\", \"iex\", \"invoke-expression\")\n| summarize Count=count() by DeviceName, InitiatingProcessFileName, ProcessCommandLine\n| sort by Count desc",
        "time_range": "last_24h",
        "fields_expected": ["DeviceName", "InitiatingProcessFileName", "ProcessCommandLine", "Count"],
        "prerequisite": "Requires Microsoft Defender for Endpoint (DeviceProcessEvents table)"
    },
    "login_failure_bruteforce": {
        "name": "Login failure (brute force detection)",
        "description": "Detect multiple failed login attempts from same source",
        "query_template": "SigninLogs\n| where TimeGenerated > ago({time_value})\n| where ResultDescription == \"Invalid credentials\" or ResultType >= 500\n| summarize Failures=count() by AppDisplayName, UserPrincipalName, IPAddress\n| where Failures >= 5\n| sort by Failures desc",
        "time_range": "last_24h",
        "fields_expected": ["AppDisplayName", "UserPrincipalName", "IPAddress", "Failures"],
        "prerequisite": "Requires Azure AD Sign-in Logs"
    },
    "lateral_movement_rdp": {
        "name": "Lateral movement via RDP",
        "description": "Detect RDP connections between internal hosts",
        "query_template": "DeviceNetworkEvents\n| where TimeGenerated > ago({time_value})\n| where RemotePort == 3389 and ActionType == \"ConnectionAllowed\"\n| summarize Count=count() by DeviceName, RemoteIP, InitiatingProcessAccountName\n| sort by Count desc",
        "time_range": "last_24h",
        "fields_expected": ["DeviceName", "RemoteIP", "InitiatingProcessAccountName", "Count"],
        "prerequisite": "Requires Microsoft Defender for Endpoint"
    },
    "lateral_movement_smb": {
        "name": "Lateral movement via SMB",
        "description": "Detect SMB connections between internal hosts (potential SMB exploitation)",
        "query_template": "DeviceNetworkEvents\n| where TimeGenerated > ago({time_value})\n| where RemotePort in (139, 445) and ActionType == \"ConnectionAllowed\"\n| summarize Count=count() by DeviceName, RemoteIP, InitiatingProcessAccountName\n| sort by Count desc",
        "time_range": "last_24h",
        "fields_expected": ["DeviceName", "RemoteIP", "InitiatingProcessAccountName", "Count"],
        "prerequisite": "Requires Microsoft Defender for Endpoint"
    },
    "file_drop_by_hash": {
        "name": "File drop by IOC hash",
        "description": "Find files with known malicious hashes",
        "query_template": "let iocHashes = dynamic({ioc_hashes});\nDeviceFileEvents\n| where TimeGenerated > ago({time_value})\n| where SHA256 in (iocHashes) or MD5 in (iocHashes) or SHA1 in (iocHashes)\n| summarize Count=count() by DeviceName, FileName, SHA256\n| sort by Count desc",
        "time_range": "last_7d",
        "fields_expected": ["DeviceName", "FileName", "SHA256", "Count"],
        "prerequisite": "Requires Microsoft Defender for Endpoint (DeviceFileEvents table)"
    },
    "host_anomaly_aggregation": {
        "name": "Host anomaly aggregation (multi-signal)",
        "description": "Find hosts with multiple suspicious activities within 1 hour",
        "query_template": "let startTime = ago(1h);\nDeviceProcessEvents\n| where Timestamp > startTime\n| summarize EventCount=count() by DeviceName, ActionType\n| where EventCount > 10\n| extend RiskScore = case(ActionType == \"ProcessCreated\", 2, ActionType == \"NetworkConnectionConnected\", 1, ActionType == \"FileCreated\", 3, 0)\n| summarize TotalRisk=sum(RiskScore) by DeviceName\n| sort by TotalRisk desc",
        "time_range": "last_1h",
        "fields_expected": ["DeviceName", "TotalRisk", "ActionType"],
        "prerequisite": "Requires Microsoft Defender for Endpoint"
    },
    "privilege_escalation": {
        "name": "Privilege escalation attempts",
        "description": "Detect processes requesting privileges or running as SYSTEM",
        "query_template": "DeviceProcessEvents\n| where TimeGenerated > ago({time_value})\n| where ProcessCommandLine has_any (\"privileges\", \"admin\", \"system\", \"sudo\", \"runas\") or AccountName == \"SYSTEM\"\n| summarize Count=count() by DeviceName, FolderPath, AccountName\n| sort by Count desc",
        "time_range": "last_24h",
        "fields_expected": ["DeviceName", "FolderPath", "AccountName", "Count"],
        "prerequisite": "Requires Microsoft Defender for Endpoint"
    },
    "new_service_creation": {
        "name": "New service creation",
        "description": "Detect creation of new Windows services (persistence mechanism)",
        "query_template": "DeviceProcessEvents\n| where TimeGenerated > ago({time_value})\n| where InitiatingProcessFileName =~ \"sc.exe\" and ProcessCommandLine has \"create\"\n| summarize Count=count() by DeviceName, ProcessCommandLine\n| sort by Count desc",
        "time_range": "last_24h",
        "fields_expected": ["DeviceName", "ProcessCommandLine", "Count"],
        "prerequisite": "Requires Microsoft Defender for Endpoint"
    },
    "scheduled_task_creation": {
        "name": "Scheduled task creation",
        "description": "Detect creation of scheduled tasks (persistence mechanism)",
        "query_template": "DeviceProcessEvents\n| where TimeGenerated > ago({time_value})\n| where InitiatingProcessFileName =~ \"schtasks.exe\" and ProcessCommandLine has_any (\"create\", \"/sc\")\n| summarize Count=count() by DeviceName, ProcessCommandLine\n| sort by Count desc",
        "time_range": "last_24h",
        "fields_expected": ["DeviceName", "ProcessCommandLine", "Count"],
        "prerequisite": "Requires Microsoft Defender for Endpoint"
    },
}


def get_queries_for_platform(platform: str) -> dict:
    """Get all query templates for a specific platform."""
    platform_queries = {
        "splunk": SPLUNK_QUERIES,
        "elastic_kql": ELASTIC_KQL_QUERIES,
        "sentinel_kql": SENTINEL_KQL_QUERIES,
    }
    return platform_queries.get(platform, {})
