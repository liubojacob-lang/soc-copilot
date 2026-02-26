#!/usr/bin/env python3
"""
Wazuh Log Forwarder
Forwards Wazuh alerts to SOC Copilot Backend
"""

import asyncio
import os
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

import httpx
from elasticsearch import AsyncElasticsearch

# Configuration
ELASTICSEARCH_URL = os.getenv("ELASTICSEARCH_URL", "http://elasticsearch:9200")
ELASTICSEARCH_USERNAME = os.getenv("ELASTICSEARCH_USERNAME", "elastic")
ELASTICSEARCH_PASSWORD = os.getenv("ELASTICSEARCH_PASSWORD", "changeme")
SOC_COPILOT_API_URL = os.getenv("SOC_COPILOT_API_URL", "http://backend:8000")
SOC_COPILOT_API_KEY = os.getenv("SOC_COPILOT_API_KEY", "")

POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "30"))
ALERT_TIME_WINDOW = os.getenv("ALERT_TIME_WINDOW", "now-5m")
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "100"))

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class WazuhLogForwarder:
    """Forward Wazuh alerts to SOC Copilot"""

    def __init__(self):
        self.es_client: Optional[AsyncElasticsearch] = None
        self.http_client: Optional[httpx.AsyncClient] = None

    async def initialize(self):
        """Initialize connections"""
        es_url = f"https://{ELASTICSEARCH_USERNAME}:{ELASTICSEARCH_PASSWORD}@elasticsearch:9200"
        
        self.es_client = AsyncElasticsearch(
            es_url,
            verify_certs=False,
            ssl_show_warn=False
        )
        
        self.http_client = httpx.AsyncClient(timeout=30.0)
        logger.info("Connections initialized")

    async def close(self):
        """Close connections"""
        if self.es_client:
            await self.es_client.close()
        if self.http_client:
            await self.http_client.close()

    async def fetch_new_alerts(self) -> List[Dict[str, Any]]:
        """Fetch new alerts from Wazuh/Elasticsearch"""
        try:
            query = {
                "query": {
                    "range": {
                        "@timestamp": {
                            "gte": ALERT_TIME_WINDOW
                        }
                    }
                },
                "size": BATCH_SIZE,
                "sort": [{"@timestamp": {"order": "desc"}}]
            }

            response = await self.es_client.search(
                index="wazuh-alerts-*",
                body=query
            )

            alerts = []
            for hit in response.get('hits', {}).get('hits', []):
                source = hit['_source']
                source['_id'] = hit['_id']
                alerts.append(source)

            logger.info(f"Fetched {len(alerts)} alerts from Wazuh")
            return alerts

        except Exception as e:
            logger.error(f"Error fetching alerts: {e}")
            return []

    def convert_to_soc_format(self, wazuh_alert: Dict[str, Any]) -> Dict[str, Any]:
        """Convert Wazuh alert format to SOC Copilot format"""
        try:
            rule = wazuh_alert.get('rule', {})
            agent = wazuh_alert.get('agent', {})
            geoip = wazuh_alert.get('geoip', {})
            data = wazuh_alert.get('data', {})

            mitre_tactics = []
            rule_mitre = rule.get('mitre', {})
            if isinstance(rule_mitre, dict):
                tactics = rule_mitre.get('tactic', [])
                if isinstance(tactics, list):
                    mitre_tactics = tactics

            rule_groups = rule.get('groups', [])
            if isinstance(rule_groups, str):
                rule_groups = [rule_groups]

            soc_alert = {
                "source": "wazuh",
                "event_id": wazuh_alert.get('_id', f"wazuh-{datetime.utcnow().timestamp()}"),
                "timestamp": wazuh_alert.get('@timestamp', datetime.utcnow().isoformat()),
                "event_type": "security_event",
                "severity": self._map_severity(rule.get('level', 0)),
                "title": rule.get('description', 'Wazuh Alert'),
                "description": rule.get('description', ''),
                "source_ip": data.get('srcip') or geoip.get('src_ip'),
                "destination_ip": data.get('dstip'),
                "protocol": data.get('protocol'),
                "agent_name": agent.get('name'),
                "agent_id": str(agent.get('id', '')),
                "agent_ip": agent.get('ip'),
                "rule_id": str(rule.get('id', '')),
                "rule_level": rule.get('level'),
                "rule_groups": rule_groups,
                "rule_mitre": mitre_tactics,
                "full_log": wazuh_alert.get('full_log'),
                "location": wazuh_alert.get('location'),
                "geoip": geoip if geoip else None,
                "raw_data": wazuh_alert
            }

            return soc_alert

        except Exception as e:
            logger.error(f"Error converting alert: {e}")
            return None

    def _map_severity(self, wazuh_level: int) -> str:
        """Map Wazuh rule level to SOC severity"""
        if wazuh_level >= 15:
            return "critical"
        elif wazuh_level >= 12:
            return "high"
        elif wazuh_level >= 8:
            return "medium"
        elif wazuh_level >= 4:
            return "low"
        else:
            return "info"

    async def forward_to_soc(self, alert: Dict[str, Any]) -> bool:
        """Forward alert to SOC Copilot"""
        try:
            headers = {"Content-Type": "application/json"}
            if SOC_COPILOT_API_KEY:
                headers["Authorization"] = f"Bearer {SOC_COPILOT_API_KEY}"

            response = await self.http_client.post(
                f"{SOC_COPILOT_API_URL}/api/v1/security-alerts/ingest",
                json=alert,
                headers=headers
            )

            if response.status_code in [200, 201]:
                return True
            else:
                logger.warning(f"Failed to forward: {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"Error forwarding alert: {e}")
            return False

    async def process_alerts(self):
        """Process and forward new alerts"""
        wazuh_alerts = await self.fetch_new_alerts()
        
        if not wazuh_alerts:
            return 0

        success_count = 0
        for wazuh_alert in wazuh_alerts:
            soc_alert = self.convert_to_soc_format(wazuh_alert)
            if soc_alert:
                if await self.forward_to_soc(soc_alert):
                    success_count += 1

        logger.info(f"Processed {len(wazuh_alerts)} alerts, {success_count} forwarded")
        return success_count


async def main():
    """Main forwarding loop"""
    forwarder = WazuhLogForwarder()

    try:
        await forwarder.initialize()
        logger.info("Wazuh Log Forwarder started")
        
        await asyncio.sleep(30)  # Wait for services

        while True:
            try:
                await forwarder.process_alerts()
                await asyncio.sleep(POLL_INTERVAL)
            except Exception as e:
                logger.error(f"Error in loop: {e}")
                await asyncio.sleep(60)

    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        await forwarder.close()


if __name__ == "__main__":
    asyncio.run(main())
