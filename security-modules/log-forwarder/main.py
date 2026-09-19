#!/usr/bin/env python3
"""
Wazuh 日志转发器
将 Wazuh 告警转发到 SOC Copilot 后端 API
"""

import asyncio
import logging
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional

import httpx
from elasticsearch import AsyncElasticsearch

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class WazuhLogForwarder:
    """Wazuh 日志转发器"""

    def __init__(self):
        # 配置
        self.wazuh_api_url = os.getenv('WAZUH_API_URL', 'http://wazuh-manager:55000')
        self.wazuh_username = os.getenv('WAZUH_API_USERNAME', 'wazuh-wui')
        # 凭据必须显式注入：'wazuh-wui' 是 Wazuh 出厂默认口令，静默使用它
        # 等于带着默认弱口令去连生产 API。
        self.wazuh_password = os.getenv('WAZUH_API_PASSWORD')
        if not self.wazuh_password:
            raise SystemExit(
                "WAZUH_API_PASSWORD is not set. Refusing to start with "
                "default/empty credentials."
            )

        self.soc_api_url = os.getenv('SOC_COPILOT_API_URL', 'http://soc-copilot-backend:8000')
        self.soc_api_key = os.getenv('SOC_COPILOT_API_KEY', '')

        self.es_url = os.getenv('ELASTICSEARCH_URL', 'http://elasticsearch:9200')
        self.es_username = os.getenv('ELASTICSEARCH_USERNAME', 'elastic')
        # 凭据必须显式注入：默认 'changeme' 会让误配静默地用弱口令打生产 ES。
        self.es_password = os.getenv('ELASTICSEARCH_PASSWORD')
        if not self.es_password:
            raise SystemExit(
                "ELASTICSEARCH_PASSWORD is not set. Refusing to start with "
                "default/empty credentials."
            )
        # TLS 校验默认开启；仅在内网自签环境显式设置 ES_VERIFY_CERTS=false 关闭
        self.es_verify_certs = os.getenv('ES_VERIFY_CERTS', 'true').lower() == 'true'

        # 客户端
        self.http_client = httpx.AsyncClient(timeout=30.0)
        self.es_client: Optional[AsyncElasticsearch] = None

        # 配置
        self.poll_interval = int(os.getenv('POLL_INTERVAL', 30))  # 秒
        self.alert_time_window = os.getenv('ALERT_TIME_WINDOW', 'now-5m')
        self.batch_size = int(os.getenv('BATCH_SIZE', 100))

    async def start(self):
        """启动转发器"""
        logger.info("=" * 60)
        logger.info("Wazuh 日志转发器启动")
        logger.info("=" * 60)
        logger.info(f"Wazuh API: {self.wazuh_api_url}")
        logger.info(f"SOC Copilot API: {self.soc_api_url}")
        logger.info(f"Elasticsearch: {self.es_url}")
        logger.info(f"轮询间隔: {self.poll_interval}秒")
        logger.info("")

        # 初始化 Elasticsearch 客户端
        try:
            self.es_client = AsyncElasticsearch(
                [self.es_url],
                basic_auth=(self.es_username, self.es_password),
                verify_ssl=self.es_verify_certs,
                request_timeout=30
            )

            # 测试连接
            info = await self.es_client.info()
            logger.info(f"已连接到 Elasticsearch: {info['cluster_name']}")

        except Exception as e:
            logger.error(f"无法连接到 Elasticsearch: {e}")
            logger.info("将使用 Wazuh API 作为备用数据源")
            self.es_client = None

        # 启动转发循环
        await self.run_forwarding_loop()

    async def run_forwarding_loop(self):
        """运行转发循环"""
        logger.info("开始转发告警...")

        while True:
            try:
                # 1. 获取新告警
                alerts = await self.fetch_new_alerts()

                if alerts:
                    logger.info(f"📊 获取到 {len(alerts)} 个新告警")

                    # 2. 转发到 SOC Copilot
                    stats = await self.forward_to_soc(alerts)

                    # 3. 统计
                    success_count = stats.get('success', 0)
                    fail_count = stats.get('failed', 0)

                    if success_count > 0:
                        logger.info(f"✅ 成功转发: {success_count}/{len(alerts)}")
                    if fail_count > 0:
                        logger.warning(f"❌ 转发失败: {fail_count}/{len(alerts)}")
                else:
                    logger.debug("无新告警")

                # 4. 等待下一次轮询
                await asyncio.sleep(self.poll_interval)

            except Exception as e:
                logger.error(f"转发循环错误: {e}")
                await asyncio.sleep(60)  # 错误后等待1分钟

    async def fetch_new_alerts(self) -> List[Dict]:
        """从 Elasticsearch 获取新告警"""
        if not self.es_client:
            return await self.fetch_from_wazuh_api()

        try:
            # 查询最近时间窗口的告警
            query = {
                "query": {
                    "range": {
                        "@timestamp": {
                            "gte": self.alert_time_window
                        }
                    }
                },
                "size": self.batch_size,
                "sort": [{"@timestamp": {"order": "asc"}}]
            }

            response = await self.es_client.search(
                index="wazuh-alerts-*",
                body=query
            )

            hits = response['hits']['hits']
            alerts = [hit['_source'] for hit in hits]

            logger.debug(f"从 Elasticsearch 获取 {len(alerts)} 个告警")
            return alerts

        except Exception as e:
            logger.error(f"从 Elasticsearch 获取告警失败: {e}")
            # 降级到 Wazuh API
            return await self.fetch_from_wazuh_api()

    async def fetch_from_wazuh_api(self) -> List[Dict]:
        """从 Wazuh API 获取告警（备用方案）"""
        try:
            async with httpx.AsyncClient() as client:
                # 获取所有告警
                response = await client.get(
                    f"{self.wazuh_api_url}/alerts/last_5m",
                    auth=(self.wazuh_username, self.wazuh_password),
                    timeout=30.0
                )

                if response.status_code == 200:
                    data = response.json()
                    alerts = data.get('data', [])
                    logger.debug(f"从 Wazuh API 获取 {len(alerts)} 个告警")
                    return alerts
                else:
                    logger.error(f"Wazuh API 返回错误: {response.status_code}")
                    return []

        except Exception as e:
            logger.error(f"从 Wazuh API 获取告警失败: {e}")
            return []

    async def forward_to_soc(self, alerts: List[Dict]) -> Dict[str, int]:
        """转发告警到 SOC Copilot"""
        stats = {'success': 0, 'failed': 0}

        for alert in alerts:
            try:
                # 转换格式
                soc_alert = self.convert_to_soc_format(alert)

                # 发送到 SOC Copilot
                success = await self.send_alert_to_soc(soc_alert)

                if success:
                    stats['success'] += 1
                    logger.debug(f"✅ 告警转发成功: {alert.get('id')}")
                else:
                    stats['failed'] += 1
                    logger.warning(f"❌ 告警转发失败: {alert.get('id')}")

            except Exception as e:
                logger.error(f"转发告警异常: {e}")
                stats['failed'] += 1

        return stats

    async def send_alert_to_soc(self, alert: Dict) -> bool:
        """发送告警到 SOC Copilot API"""
        try:
            headers = {}
            if self.soc_api_key:
                headers['X-API-Key'] = self.soc_api_key

            response = await self.http_client.post(
                f"{self.soc_api_url}/api/v1/alerts/ingest",
                json=alert,
                headers=headers,
                timeout=10.0
            )

            if response.status_code in [200, 201]:
                return True
            else:
                logger.error(f"SOC API 返回错误: {response.status_code} - {response.text}")
                return False

        except Exception as e:
            logger.error(f"发送告警到 SOC 失败: {e}")
            return False

    def convert_to_soc_format(self, wazuh_alert: Dict) -> Dict:
        """转换 Wazuh 告警为 SOC Copilot 格式"""
        rule = wazuh_alert.get('rule', {})
        agent = wazuh_alert.get('agent', {})
        src_ip = wazuh_alert.get('src_ip')
        dst_ip = wazuh_alert.get('dst_ip')

        return {
            "source": "wazuh",
            "event_id": wazuh_alert.get('id'),
            "timestamp": wazuh_alert.get('@timestamp'),
            "event_type": self.map_event_type(rule),
            "severity": self.map_severity(rule.get('level', 0)),
            "title": rule.get('description', 'Security Alert'),
            "description": self.generate_description(wazuh_alert),
            "source_ip": src_ip,
            "destination_ip": dst_ip,
            "protocol": wazuh_alert.get('protocol'),
            "agent_name": agent.get('name'),
            "agent_id": agent.get('id'),
            "agent_ip": agent.get('ip'),
            "rule_id": str(rule.get('id')),
            "rule_level": rule.get('level'),
            "rule_groups": rule.get('groups', []),
            "rule_mitre": self.extract_mitre_tactics(rule),
            "full_log": wazuh_alert.get('full_log'),
            "location": wazuh_alert.get('location'),
            "geoip": wazuh_alert.get('geoip'),
            "raw_data": wazuh_alert
        }

    def map_event_type(self, rule: Dict) -> str:
        """映射事件类型"""
        groups = rule.get('groups', [])

        group_mapping = {
            'web': 'web_attack',
            'web_attack': 'web_attack',
            'authentication': 'authentication',
            'authentication_failed': 'authentication',
            'malware': 'malware',
            'malicious_code': 'malware',
            'scan': 'reconnaissance',
            'reconnaissance': 'reconnaissance',
            'policy': 'policy_violation',
            'policy_violation': 'policy_violation',
            'ids': 'intrusion_detection',
            'firewall': 'firewall',
            'suspicious': 'suspicious_activity'
        }

        for group in groups:
            if group in group_mapping:
                return group_mapping[group]

        return 'other'

    def map_severity(self, level: int) -> str:
        """映射严重级别"""
        if level >= 15:
            return 'critical'
        elif level >= 12:
            return 'high'
        elif level >= 8:
            return 'medium'
        elif level >= 4:
            return 'low'
        else:
            return 'info'

    def generate_description(self, alert: Dict) -> str:
        """生成告警描述"""
        parts = []

        # 规则信息
        rule = alert.get('rule', {})
        parts.append(f"Rule: {rule.get('description', 'Unknown')}")

        # 代理信息
        agent = alert.get('agent', {})
        if agent.get('name'):
            parts.append(f"Agent: {agent.get('name')} ({agent.get('id')})")

        # 网络信息
        src_ip = alert.get('src_ip')
        dst_ip = alert.get('dst_ip')
        if src_ip:
            parts.append(f"Source: {src_ip}")
        if dst_ip:
            parts.append(f"Destination: {dst_ip}")

        # 地理位置
        geoip = alert.get('geoip')
        if geoip and geoip.get('country_name'):
            parts.append(f"Country: {geoip.get('country_name')}")

        # 日志
        full_log = alert.get('full_log')
        if full_log:
            log_preview = full_log[:200] + "..." if len(full_log) > 200 else full_log
            parts.append(f"Log: {log_preview}")

        return " | ".join(parts)

    def extract_mitre_tactics(self, rule: Dict) -> List[str]:
        """提取 MITRE ATT&CK 战术"""
        mitre = rule.get('mitre', {})
        tactics = mitre.get('tactics', [])
        techniques = mitre.get('techniques', [])

        all_techniques = []
        all_techniques.extend(tactics)
        all_techniques.extend([t.get('id', '') for t in techniques])

        return list(set(all_techniques))


async def main():
    """主函数"""
    forwarder = WazuhLogForwarder()
    await forwarder.start()


if __name__ == '__main__':
    asyncio.run(main())
