#!/usr/bin/env python3
"""
Wazuh Alert Mapper
Maps Wazuh events/alerts to SOC Copilot internal alert schema
"""

from datetime import datetime
from typing import Dict, Any, Optional, List
import logging
import re

logger = logging.getLogger(__name__)


class WazuhAlertMapper:
    """
    Maps Wazuh alerts to SOC Copilot alert format
    """

    # Wazuh rule level to SOC severity mapping
    SEVERITY_MAPPING = {
        # Low severity (levels 0-3)
        range(0, 4): 'low',

        # Medium severity (levels 4-7)
        range(4, 8): 'medium',

        # High severity (levels 8-12)
        range(8, 13): 'high',

        # Critical severity (levels 13-15)
        range(13, 16): 'critical'
    }

    # Common MITRE ATT&CK technique mappings
    MITRE_TECHNIQUES = {
        # Initial Access
        'T1190': 'Exploit Public-Facing Application',
        'T1078': 'Valid Accounts',
        'T1110': 'Brute Force',

        # Execution
        'T1059': 'Command and Scripting Interpreter',
        'T1203': 'Exploitation for Client Execution',
        'T1204': 'User Execution',

        # Persistence
        'T1543': 'Create or Modify System Process',
        'T1547': 'Boot or Logon Autostart Execution',
        'T1053': 'Scheduled Task/Job',

        # Privilege Escalation
        'T1068': 'Exploitation for Privilege Escalation',
        'T1484': 'Domain Policy Modification',

        # Defense Evasion
        'T1562': 'Impair Defenses',
        'T1112': 'Modify Registry',
        'T1036': 'Masquerading',

        # Credential Access
        'T1003': 'OS Credential Dumping',
        'T1111': 'Two-Factor Authentication Interception',
        'T1056': 'Input Capture',

        # Discovery
        'T1018': 'Remote File Copy',
        'T1083': 'File and Directory Discovery',
        'T1046': 'Network Service Scanning',
        'T1016': 'System Network Configuration Discovery',
        'T1007': 'System Service Discovery',
        'T1069': 'Permission Groups Discovery',

        # Lateral Movement
        'T1021': 'Remote Services',
        'T1077': 'Windows Admin Shares',
        'T1091': 'Replication Through Removable Media',

        # Collection
        'T1005': 'Data from Local System',
        'T1033': 'System Owner/User Discovery',
        'T1039': 'Data from Network Shared Drive',

        # Exfiltration
        'T1041': 'Exfiltration Over C2 Channel',
        'T1048': 'Exfiltration Over Alternative Protocol',
        'T1567': 'Exfiltration Over Web Service',

        # Impact
        'T1486': 'Data Encrypted for Impact',
        'T1485': 'Data Destruction',
        'T1489': 'Service Stop',
        'T1565': 'Data Manipulation',

        # Command and Control
        'T1071': 'Application Layer Protocol',
        'T1095': 'Non-Application Layer Protocol',
        'T1102': 'Web Service'
    }

    def __init__(self):
        """Initialize mapper"""
        logger.info("WazuhAlertMapper initialized")

    def map_alert(self, wazuh_alert: Dict[str, Any]) -> Dict[str, Any]:
        """
        Map Wazuh alert to SOC Copilot format

        Args:
            wazuh_alert: Raw Wazuh alert dictionary

        Returns:
            Mapped alert in SOC Copilot format
        """
        try:
            # Extract rule information
            rule = wazuh_alert.get('rule', {})

            # Extract agent information
            agent = wazuh_alert.get('agent', {})

            # Extract location information
            location = wazuh_alert.get('location', '')

            # Extract full log
            full_log = wazuh_alert.get('full_log', '')

            # Extract timestamp
            timestamp = wazuh_alert.get('timestamp', datetime.utcnow().isoformat())

            # Map severity
            rule_level = rule.get('level', 0)
            severity = self._map_severity(rule_level)

            # Create alert ID
            alert_id = self._generate_alert_id(
                agent_id=agent.get('id', 'unknown'),
                rule_id=rule.get('id', 0),
                timestamp=timestamp
            )

            # Build mapped alert
            mapped_alert = {
                'id': alert_id,
                'source': 'wazuh',
                'source_reference': f"wazuh-{agent.get('id', 'unknown')}-{timestamp}",

                # Event classification
                'event_type': self._determine_event_type(rule, full_log),
                'severity': severity,
                'title': rule.get('description', 'Security Event Detected'),
                'description': self._build_description(wazuh_alert),

                # Network information
                'source_ip': self._extract_source_ip(wazuh_alert),
                'destination_ip': agent.get('ip', 'N/A'),
                'source_port': self._extract_source_port(wazuh_alert),
                'destination_port': self._extract_destination_port(wazuh_alert),
                'protocol': self._extract_protocol(wazuh_alert),

                # Agent/Host information
                'agent_name': agent.get('name', 'Unknown'),
                'agent_id': agent.get('id', 'N/A'),
                'agent_ip': agent.get('ip', 'N/A'),
                'agent_version': agent.get('version', 'N/A'),
                'location': location,

                # Rule information
                'rule_id': str(rule.get('id', 'N/A')),
                'rule_level': rule_level,
                'rule_groups': rule.get('groups', []),
                'rule_description': rule.get('description', ''),
                'rule_mitre': self._extract_mitre_techniques(rule),

                # User information (if available)
                'user': self._extract_user(wazuh_alert),
                'user_name': self._extract_user(wazuh_alert),

                # File information (if applicable)
                'file_path': self._extract_file_path(wazuh_alert),
                'file_name': self._extract_file_name(wazuh_alert),

                # Process information (if applicable)
                'process_name': self._extract_process_name(wazuh_alert),
                'process_id': self._extract_process_id(wazuh_alert),

                # Attack details
                'attack_category': self._determine_attack_category(rule, full_log),
                'attack_stage': self._determine_attack_stage(rule, full_log),
                'confidence': self._calculate_confidence(wazuh_alert),

                # MITRE ATT&CK
                'mitre_attack_id': rule.get('mitre', {}).get('id', []),
                'mitre_attack_technique': rule.get('mitre', {}).get('technique', []),

                # GeoIP (if available)
                'geoip': self._extract_geoip(wazuh_alert),

                # Compliance
                'compliance': self._extract_compliance(wazuh_alert),

                # Timestamps
                'created_at': datetime.utcnow().isoformat(),
                'event_timestamp': timestamp,
                'updated_at': datetime.utcnow().isoformat(),

                # Raw data for reference
                'raw_data': {
                    'wazuh_alert': wazuh_alert
                }
            }

            # Add enrichment data
            mapped_alert['enrichment'] = {
                'is_false_positive_candidate': self._is_false_positive_candidate(mapped_alert),
                'requires_investigation': self._requires_investigation(mapped_alert),
                'suggested_actions': self._suggest_actions(mapped_alert)
            }

            logger.debug(f"Mapped alert {alert_id} (severity: {severity})")
            return mapped_alert

        except Exception as e:
            logger.error(f"Error mapping alert: {e}", exc_info=True)
            # Return minimal alert structure
            return {
                'id': f"WAZUH-MAPPING-ERROR-{datetime.utcnow().isoformat()}",
                'source': 'wazuh',
                'severity': 'medium',
                'title': 'Alert Mapping Error',
                'description': str(e),
                'raw_data': {'wazuh_alert': wazuh_alert}
            }

    def _map_severity(self, rule_level: int) -> str:
        """
        Map Wazuh rule level to SOC severity

        Args:
            rule_level: Wazuh rule level (0-15)

        Returns:
            SOC severity (low, medium, high, critical)
        """
        for level_range, severity in self.SEVERITY_MAPPING.items():
            if rule_level in level_range:
                return severity
        return 'medium'  # Default

    def _generate_alert_id(self, agent_id: str, rule_id: int, timestamp: str) -> str:
        """
        Generate unique alert ID

        Args:
            agent_id: Agent ID
            rule_id: Rule ID
            timestamp: Event timestamp

        Returns:
            Unique alert ID
        """
        # Format: WAZUH-AGENTID-RULEID-TIMESTAMP
        ts_clean = timestamp.replace(':', '-').replace('.', '-')[:19]
        return f"WAZUH-{agent_id}-{rule_id}-{ts_clean}"

    def _determine_event_type(self, rule: Dict, full_log: str) -> str:
        """
        Determine event type from rule and log

        Args:
            rule: Rule dictionary
            full_log: Full log text

        Returns:
            Event type string
        """
        groups = rule.get('groups', [])

        # Check rule groups for event type hints
        if 'authentication_failed' in groups or 'authentication_success' in groups:
            return 'authentication'
        elif any(g in groups for g in ['web', 'web_attack', 'sql_injection', 'xss']):
            return 'web_attack'
        elif any(g in groups for g in ['virus', 'malware', 'trojan', 'ransomware']):
            return 'malware'
        elif any(g in groups for g in ['scan', 'recon', 'enumeration']):
            return 'reconnaissance'
        elif any(g in groups for g in ['bruteforce', 'brute_force']):
            return 'brute_force'
        elif any(g in groups for g in ['intrusion', 'ids', 'ips']):
            return 'intrusion_detection'
        elif any(g in groups for g in ['policy', 'compliance', 'audit']):
            return 'policy_violation'
        elif any(g in groups for g in ['syscheck', 'fim', 'integrity']):
            return 'file_integrity'
        elif any(g in groups for g in ['rootcheck', 'rootkit']):
            return 'rootkit_detection'
        elif 'squid' in groups or 'web-accesslog' in groups:
            return 'web_access'
        else:
            return 'security_event'

    def _build_description(self, wazuh_alert: Dict) -> str:
        """
        Build human-readable alert description

        Args:
            wazuh_alert: Raw Wazuh alert

        Returns:
            Formatted description
        """
        rule = wazuh_alert.get('rule', {})
        agent = wazuh_alert.get('agent', {})
        full_log = wazuh_alert.get('full_log', '')

        description_parts = [
            f"**Rule**: {rule.get('description', 'Unknown Rule')}",
            f"**Level**: {rule.get('level', 0)}",
            ""
        ]

        # Add agent info
        if agent.get('name'):
            description_parts.extend([
                "**Agent Information**",
                f"• Name: {agent.get('name')}",
                f"• ID: {agent.get('id')}",
                f"• IP: {agent.get('ip', 'N/A')}",
                ""
            ])

        # Add source information
        src_ip = self._extract_source_ip(wazuh_alert)
        if src_ip:
            description_parts.extend([
                "**Source**",
                f"• IP: {src_ip}",
                ""
            ])

        # Add rule groups
        groups = rule.get('groups', [])
        if groups:
            description_parts.extend([
                "**Categories**",
                f"• {', '.join(groups[:10])}",  # Limit to 10 groups
                ""
            ])

        # Add MITRE techniques
        mitre = rule.get('mitre', {})
        if mitre.get('technique'):
            techniques = mitre.get('technique', [])
            if isinstance(techniques, list):
                description_parts.extend([
                    "**MITRE ATT&CK**",
                    *[f"• {t}" for t in techniques[:5]],
                    ""
                ])

        # Add log excerpt
        if full_log and len(full_log) < 500:
            description_parts.extend([
                "**Event Log**",
                f"```{full_log}```"
            ])
        elif full_log:
            description_parts.extend([
                "**Event Log**",
                f"```{full_log[:500]}...```"
            ])

        return '\n'.join(description_parts)

    def _extract_source_ip(self, wazuh_alert: Dict) -> str:
        """Extract source IP from alert"""
        return wazuh_alert.get('data', {}).get('srcip') or \
               wazuh_alert.get('srcip', 'N/A')

    def _extract_source_port(self, wazuh_alert: Dict) -> str:
        """Extract source port from alert"""
        return wazuh_alert.get('data', {}).get('srcport') or \
               wazuh_alert.get('srcport', 'N/A')

    def _extract_destination_port(self, wazuh_alert: Dict) -> str:
        """Extract destination port from alert"""
        return wazuh_alert.get('data', {}).get('dstport') or \
               wazuh_alert.get('dstport', 'N/A')

    def _extract_protocol(self, wazuh_alert: Dict) -> str:
        """Extract protocol from alert"""
        return wazuh_alert.get('data', {}).get('protocol') or \
               wazuh_alert.get('protocol', 'N/A')

    def _extract_user(self, wazuh_alert: Dict) -> str:
        """Extract username from alert"""
        return wazuh_alert.get('data', {}).get('audit', {}).get('user', {}).get('name') or \
               wazuh_alert.get('data', {}).get('win', {}).get('eventdata', {}).get('user') or \
               wazuh_alert.get('data', {}).get('srcuser', 'N/A')

    def _extract_file_path(self, wazuh_alert: Dict) -> str:
        """Extract file path from alert"""
        return wazuh_alert.get('data', {}).get('path', 'N/A')

    def _extract_file_name(self, wazuh_alert: Dict) -> str:
        """Extract file name from alert"""
        path = self._extract_file_path(wazuh_alert)
        if path and path != 'N/A':
            return path.split('/')[-1]
        return 'N/A'

    def _extract_process_name(self, wazuh_alert: Dict) -> str:
        """Extract process name from alert"""
        return wazuh_alert.get('data', {}).get('process', {}).get('name', 'N/A')

    def _extract_process_id(self, wazuh_alert: Dict) -> str:
        """Extract process ID from alert"""
        return str(wazuh_alert.get('data', {}).get('process', {}).get('pid', 'N/A'))

    def _extract_geoip(self, wazuh_alert: Dict) -> Dict[str, str]:
        """Extract GeoIP information from alert"""
        geoip = wazuh_alert.get('data', {}).get('geoip', {})
        if geoip:
            return {
                'country_code': geoip.get('country_code', 'N/A'),
                'country_name': geoip.get('country_name', 'N/A'),
                'city': geoip.get('city_name', 'N/A')
            }
        return {}

    def _extract_mitre_techniques(self, rule: Dict) -> List[str]:
        """Extract MITRE ATT&CK technique IDs"""
        mitre = rule.get('mitre', {})
        if isinstance(mitre, dict):
            techniques = mitre.get('id', [])
            if isinstance(techniques, list):
                return techniques
            elif isinstance(techniques, str):
                return [techniques]
        return []

    def _extract_compliance(self, wazuh_alert: Dict) -> Dict[str, Any]:
        """Extract compliance information"""
        return wazuh_alert.get('data', {}).get('compliance', {})

    def _determine_attack_category(self, rule: Dict, full_log: str) -> str:
        """Determine attack category"""
        groups = rule.get('groups', [])

        category_map = {
            'authentication_failed': 'Credential Theft',
            'bruteforce': 'Brute Force',
            'web': 'Web Application Attack',
            'sql_injection': 'SQL Injection',
            'virus': 'Malware',
            'ransomware': 'Ransomware',
            'scan': 'Reconnaissance',
            'rootcheck': 'Rootkit',
            'syscheck': 'File Integrity'
        }

        for group in groups:
            if group in category_map:
                return category_map[group]

        return 'Unknown'

    def _determine_attack_stage(self, rule: Dict, full_log: str) -> str:
        """Determine attack stage"""
        groups = rule.get('groups', [])

        if any(g in groups for g in ['scan', 'recon']):
            return 'Reconnaissance'
        elif any(g in groups for g in ['exploit', 'web_attack']):
            return 'Exploitation'
        elif any(g in groups for g in ['virus', 'trojan', 'malware']):
            return 'Delivery & Installation'
        elif any(g in groups for g in ['rootkit', 'persistence']):
            return 'Establish Foothold'
        elif 'lateral_movement' in groups:
            return 'Lateral Movement'
        elif 'exfiltration' in groups:
            return 'Exfiltration'
        elif 'ransomware' in groups or 'impact' in groups:
            return 'Impact'
        else:
            return 'Unknown'

    def _calculate_confidence(self, wazuh_alert: Dict) -> str:
        """Calculate confidence level"""
        rule_level = wazuh_alert.get('rule', {}).get('level', 0)

        if rule_level >= 13:
            return 'High'
        elif rule_level >= 8:
            return 'Medium'
        else:
            return 'Low'

    def _is_false_positive_candidate(self, mapped_alert: Dict) -> bool:
        """Check if alert might be a false positive"""
        # Low severity alerts are more likely to be false positives
        if mapped_alert.get('severity') == 'low':
            return True

        # Known high-false-positive patterns
        rule_id = mapped_alert.get('rule_id')
        if rule_id in ['550', '551', '552']:  # Common noisy rules
            return True

        return False

    def _requires_investigation(self, mapped_alert: Dict) -> bool:
        """Check if alert requires investigation"""
        severity = mapped_alert.get('severity', '')
        return severity in ['high', 'critical']

    def _suggest_actions(self, mapped_alert: Dict) -> List[str]:
        """Suggest response actions based on alert type"""
        actions = []

        event_type = mapped_alert.get('event_type', '')
        severity = mapped_alert.get('severity', '')

        if event_type == 'authentication':
            actions.extend([
                'Verify user identity',
                'Check if login location is unusual',
                'Consider temporary account lockout'
            ])
        elif event_type == 'brute_force':
            actions.extend([
                'Block source IP at firewall',
                'Check for successful logins from this IP',
                'Notify affected user'
            ])
        elif event_type == 'malware':
            actions.extend([
                'Isolate affected host',
                'Run full system scan',
                'Check for lateral movement',
                'Preserve forensic evidence'
            ])
        elif event_type == 'web_attack':
            actions.extend([
                'Review web server logs',
                'Check for successful exploits',
                'Implement WAF rule if needed'
            ])
        elif event_type == 'reconnaissance':
            actions.extend([
                'Monitor for follow-up activity',
                'Identify attacker motivation',
                'Consider blocking scanning source'
            ])

        # Add severity-specific actions
        if severity == 'critical':
            actions.insert(0, '🚨 IMMEDIATE RESPONSE REQUIRED')

        return actions if actions else ['Review alert details', 'Check for related events']


# Singleton instance
_alert_mapper: Optional[WazuhAlertMapper] = None


def get_alert_mapper() -> WazuhAlertMapper:
    """Get alert mapper singleton"""
    global _alert_mapper
    if _alert_mapper is None:
        _alert_mapper = WazuhAlertMapper()
    return _alert_mapper
