"""
Alert Enrichment Service
Automatically enrich security alerts with threat intelligence data
"""

import asyncio
from typing import Dict, Any, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import httpx

from db.session import AsyncSessionLocal
from models.security_alert import SecurityAlert
from core.logger import get_logger

logger = get_logger(__name__)


class ThreatIntelEnricher:
    """Enrich alerts with threat intelligence from multiple sources"""

    def __init__(self):
        self.client = None
        self.sources = {
            'virustotal': False,  # Requires API key
            'abuseipdb': False,   # Requires API key
            'otx': True,          # OTX is free
        }

    async def __aenter__(self):
        self.client = httpx.AsyncClient(timeout=10.0)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.client:
            await self.client.aclose()

    async def enrich_alert(self, alert: SecurityAlert) -> Dict[str, Any]:
        """
        Enrich a single alert with threat intelligence

        Returns enrichment data to be stored in alert
        """
        enrichment = {
            'enriched_at': datetime.utcnow().isoformat(),
            'indicators': {},
            'threat_scores': {},
            'tags': [],
        }

        # Enrich source IP
        if alert.source_ip:
            ip_data = await self._enrich_ip(alert.source_ip)
            enrichment['indicators']['source_ip'] = ip_data

        # Enrich destination IP
        if alert.destination_ip:
            ip_data = await self._enrich_ip(alert.destination_ip)
            enrichment['indicators']['destination_ip'] = ip_data

        # Enrich based on MITRE tactics
        if alert.rule_mitre:
            tactic_info = await self._get_mitre_info(alert.rule_mitre)
            enrichment['mitre_info'] = tactic_info

        return enrichment

    async def _enrich_ip(self, ip: str) -> Dict[str, Any]:
        """Enrich an IP address with threat intelligence"""
        result = {
            'ip': ip,
            'reputation': 'unknown',
            'scores': {},
            'tags': [],
            'first_seen': None,
            'last_seen': None,
        }

        # Check AbuseIPDB (if API key available)
        if self.sources.get('abuseipdb'):
            abuse_data = await self._check_abuseipdb(ip)
            if abuse_data:
                result['scores']['abuseipdb'] = abuse_data.get('abuse_confidence_score', 0)
                result['tags'].extend(abuse_data.get('reports', []))

        # Check OTX AlienVault (always available)
        otx_data = await self._check_otx_ip(ip)
        if otx_data:
            result['reputation'] = 'malicious' if otx_data.get('reputation', 0) > 0 else 'clean'
            result['scores']['otx'] = otx_data.get('reputation', 0)
            result['tags'].extend(otx_data.get('pulse_info', {}).get('pulses', []))

        return result

    async def _check_otx_ip(self, ip: str) -> Optional[Dict]:
        """Check IP reputation against AlienVault OTX"""
        try:
            url = f"https://otx.alienvault.com/api/v1/indicators/IPv4/{ip}/reputation"
            response = await self.client.get(url)

            if response.status_code == 200:
                data = response.json()
                return {
                    'reputation': data.get('reputation', 0),
                    'pulse_info': data.get('pulse_info', {}),
                }
        except Exception as e:
            logger.warning(f"OTX IP lookup failed for {ip}: {e}")

        return None

    async def _check_abuseipdb(self, ip: str) -> Optional[Dict]:
        """Check IP against AbuseIPDB (requires API key)"""
        # TODO: Add when API key is available
        return None

    async def _get_mitre_info(self, mitre_csv: str) -> Dict[str, Any]:
        """Get information about MITRE ATT&CK tactics"""
        tactics = [t.strip() for t in mitre_csv.split(',') if t.strip()]

        mitre_info = {}
        for tactic in tactics:
            # MITRE ATT&CK tactic mappings
            tactic_details = self._get_tactic_details(tactic)
            if tactic_details:
                mitre_info[tactic] = tactic_details

        return mitre_info

    def _get_tactic_details(self, tactic_id: str) -> Optional[Dict]:
        """Get details about a MITRE tactic"""
        # Common MITRE ATT&CK tactics mapping
        tactics_db = {
            'TA0001': {
                'name': 'Initial Access',
                'description': 'The adversary is trying to get into your network',
                'techniques': ['T1190', 'T1078', 'T1133'],
            },
            'TA0002': {
                'name': 'Execution',
                'description': 'The adversary is trying to run malicious code',
                'techniques': ['T1203', 'T1059', 'T1204'],
            },
            'TA0003': {
                'name': 'Persistence',
                'description': 'The adversary is trying to maintain their foothold',
                'techniques': ['T1543', 'T1053', 'T1547'],
            },
            'TA0004': {
                'name': 'Privilege Escalation',
                'description': 'The adversary is trying to gain higher-level permissions',
                'techniques': ['T1068', 'T1488', 'T1548'],
            },
            'TA0005': {
                'name': 'Defense Evasion',
                'description': 'The adversary is trying to avoid being detected',
                'techniques': ['T1562', 'T1070', 'T1027'],
            },
            'TA0006': {
                'name': 'Credential Access',
                'description': 'The adversary is trying to steal account names and passwords',
                'techniques': ['T1003', 'T1552', 'T1110'],
            },
            'TA0007': {
                'name': 'Discovery',
                'description': 'The adversary is trying to figure out your environment',
                'techniques': ['T1087', 'T1033', 'T1018'],
            },
            'TA0008': {
                'name': 'Lateral Movement',
                'description': 'The adversary is trying to move through your network',
                'techniques': ['T1021', 'T1077', 'T1563'],
            },
            'TA0009': {
                'name': 'Collection',
                'description': 'The adversary is trying to gather data of interest',
                'techniques': ['T1005', 'T1113', 'T1125'],
            },
            'TA0010': {
                'name': 'Exfiltration',
                'description': 'The adversary is trying to steal data',
                'techniques': ['T1041', 'T1567', 'T1030'],
            },
            'TA0011': {
                'name': 'Command and Control',
                'description': 'The adversary is trying to communicate with compromised systems',
                'techniques': ['T1071', 'T1095', 'T1102'],
            },
            'TA0040': {
                'name': 'Impact',
                'description': 'The adversary is trying to manipulate, interrupt, or destroy your systems',
                'techniques': ['T1486', 'T1485', 'T1489'],
            },
        }

        return tactics_db.get(tactic_id)


class AlertEnrichmentService:
    """Service to automatically enrich new alerts"""

    def __init__(self):
        self.enricher = ThreatIntelEnricher()

    async def process_alert(self, alert_id: int) -> bool:
        """
        Process a single alert for enrichment

        Returns True if enrichment was successful
        """
        try:
            async with AsyncSessionLocal() as session:
                query = select(SecurityAlert).where(SecurityAlert.id == alert_id)
                result = await session.execute(query)
                alert = result.scalar_one_or_none()

                if not alert:
                    logger.warning(f"Alert {alert_id} not found for enrichment")
                    return False

                # Skip if already enriched recently
                if alert.raw_data and alert.raw_data.get('enriched_at'):
                    # Check if enriched in last 24h
                    enriched_at = datetime.fromisoformat(alert.raw_data['enriched_at'])
                    if (datetime.utcnow() - enriched_at).days < 1:
                        logger.debug(f"Alert {alert_id} already enriched recently")
                        return False

                # Perform enrichment
                async with self.enricher as enricher:
                    enrichment = await enricher.enrich_alert(alert)

                # Update alert with enrichment data
                if not alert.raw_data:
                    alert.raw_data = {}

                alert.raw_data['threat_intel'] = enrichment
                await session.commit()

                logger.info(
                    f"Alert {alert_id} enriched with threat intel: "
                    f"{len(enrichment.get('indicators', {}))} indicators checked"
                )
                return True

        except Exception as e:
            logger.error(f"Error enriching alert {alert_id}: {e}")
            return False

    async def process_recent_alerts(self, hours: int = 1) -> int:
        """
        Process all alerts from the last N hours

        Returns count of enriched alerts
        """
        try:
            async with AsyncSessionLocal() as session:
                from datetime import timedelta

                cutoff = datetime.utcnow() - timedelta(hours=hours)

                query = select(SecurityAlert).where(
                    SecurityAlert.created_at >= cutoff
                ).order_by(SecurityAlert.created_at.desc())

                result = await session.execute(query)
                alerts = result.scalars().all()

                logger.info(f"Found {len(alerts)} alerts to enrich from last {hours}h")

                enriched_count = 0
                for alert in alerts:
                    success = await self.process_alert(alert.id)
                    if success:
                        enriched_count += 1

                return enriched_count

        except Exception as e:
            logger.error(f"Error processing recent alerts: {e}")
            return 0


# Background task to continuously enrich alerts
async def enrichment_worker():
    """Background worker that continuously enriches new alerts"""
    service = AlertEnrichmentService()

    logger.info("Starting alert enrichment worker")

    while True:
        try:
            # Process alerts from last hour
            count = await service.process_recent_alerts(hours=1)

            if count > 0:
                logger.info(f"Enriched {count} alerts in this cycle")

            # Wait before next cycle
            await asyncio.sleep(300)  # 5 minutes

        except Exception as e:
            logger.error(f"Error in enrichment worker: {e}")
            await asyncio.sleep(60)  # Wait 1 minute before retry
