#!/usr/bin/env python3
"""
Wazuh Log Receiver Service
Continuously polls Wazuh API for new events and publishes to message queue
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import backoff

from .wazuh_client import WazuhClient, get_wazuh_client
from .wazuh_alert_mapper import WazuhAlertMapper, get_alert_mapper
from .event_bus import get_event_bus

logger = logging.getLogger(__name__)


class WazuhLogReceiver:
    """
    Service that continuously receives logs from Wazuh and publishes to message queue
    """

    def __init__(
        self,
        poll_interval: int = 30,
        batch_size: int = 100,
        lookback_minutes: int = 5,
        enabled: bool = True
    ):
        """
        Initialize Wazuh log receiver

        Args:
            poll_interval: Seconds between polling cycles (default: 30)
            batch_size: Maximum events to fetch per poll (default: 100)
            lookback_minutes: Minutes to look back for initial fetch (default: 5)
            enabled: Whether receiver is enabled (default: True)
        """
        self.poll_interval = poll_interval
        self.batch_size = batch_size
        self.lookback_minutes = lookback_minutes
        self.enabled = enabled

        # Components
        self.wazuh_client: Optional[WazuhClient] = None
        self.alert_mapper = get_alert_mapper()
        self.event_bus = get_event_bus()

        # State tracking
        self.last_poll_time: Optional[datetime] = None
        self.total_events_received = 0
        self.total_alerts_published = 0
        self.total_errors = 0
        self.is_running = False

        logger.info(
            f"WazuhLogReceiver initialized (poll_interval={poll_interval}s, "
            f"batch_size={batch_size}, lookback={lookback_minutes}min)"
        )

    @backoff.on_exception(
        backoff.expo,
        Exception,
        max_tries=5,
        base=2,
        max_value=60
    )
    async def start(self):
        """
        Start the log receiver service
        Continuously polls Wazuh for new events
        """
        if not self.enabled:
            logger.info("WazuhLogReceiver is disabled, not starting")
            return

        if self.is_running:
            logger.warning("WazuhLogReceiver is already running")
            return

        self.is_running = True
        logger.info("Starting WazuhLogReceiver service...")

        # Initialize Wazuh client
        self.wazuh_client = get_wazuh_client()
        if not self.wazuh_client:
            logger.error("Wazuh client not initialized, cannot start receiver")
            self.is_running = False
            return

        # Initialize last poll time (look back to catch recent events)
        self.last_poll_time = datetime.utcnow() - timedelta(minutes=self.lookback_minutes)

        logger.info(f"Initial poll time set to {self.last_poll_time.isoformat()}")

        # Start polling loop
        try:
            while self.is_running:
                await self._poll_cycle()
                await asyncio.sleep(self.poll_interval)
        except asyncio.CancelledError:
            logger.info("WazuhLogReceiver cancelled")
        except Exception as e:
            logger.error(f"Fatal error in WazuhLogReceiver: {e}", exc_info=True)
        finally:
            self.is_running = False
            logger.info("WazuhLogReceiver stopped")

    async def stop(self):
        """Stop the log receiver service"""
        logger.info("Stopping WazuhLogReceiver...")
        self.is_running = False

    async def _poll_cycle(self):
        """
        Execute one polling cycle
        Fetch events from Wazuh and publish to message queue
        """
        try:
            logger.debug(f"Starting poll cycle from {self.last_poll_time.isoformat()}")

            # Fetch events from Wazuh
            events = await self._fetch_events()

            if events:
                logger.info(f"Fetched {len(events)} events from Wazuh")
                self.total_events_received += len(events)

                # Process and publish alerts
                published_count = await self._process_events(events)
                self.total_alerts_published += published_count

                # Update last poll time
                self.last_poll_time = datetime.utcnow()

                logger.info(
                    f"Poll cycle completed: {len(events)} events received, "
                    f"{published_count} alerts published"
                )
            else:
                logger.debug("No new events from Wazuh")

        except Exception as e:
            logger.error(f"Error in poll cycle: {e}", exc_info=True)
            self.total_errors += 1

    async def _fetch_events(self) -> list:
        """
        Fetch events from Wazuh API

        Returns:
            List of Wazuh events
        """
        if not self.wazuh_client:
            logger.warning("Wazuh client not available")
            return []

        try:
            # Fetch alerts (not raw events - alerts are pre-processed by Wazuh)
            alerts = await self.wazuh_client.get_alerts(
                limit=self.batch_size,
                start_time=self.last_poll_time,
                end_time=datetime.utcnow()
            )

            logger.debug(f"Fetched {len(alerts)} alerts from Wazuh API")
            return alerts

        except Exception as e:
            logger.error(f"Error fetching events from Wazuh: {e}", exc_info=True)
            return []

    async def _process_events(self, events: list) -> int:
        """
        Process Wazuh events and publish to message queue and stream service

        Args:
            events: List of Wazuh events/alerts

        Returns:
            Number of alerts successfully published
        """
        published_count = 0

        # Get stream service if available
        from .wazuh_stream_service import get_wazuh_stream_service
        stream_service = None
        try:
            stream_service = get_wazuh_stream_service()
        except Exception:
            pass  # Stream service not initialized, skip streaming

        for event in events:
            try:
                # Map Wazuh event to SOC Copilot alert format
                mapped_alert = self.alert_mapper.map_alert(event)

                # Determine queue priority based on severity
                severity = mapped_alert.get('severity', 'medium')
                queue_priority = self._severity_to_queue(severity)

                # Publish to message queue
                await self.event_bus.publish(
                    event_type="wazuh.alert.polled",
                    source="wazuh-poller",
                    payload={"normalized_alert": mapped_alert, "raw_event": event},
                    event_id=str(mapped_alert.get("id", event.get("id", "unknown"))),
                    priority=queue_priority,
                    metadata={"ingest": "polling"},
                )

                published_count += 1

                # Also send to stream service if available
                if stream_service and stream_service._running:
                    try:
                        from schemas.wazuh_stream import WazuhAlertStream, SeverityLevel
                        from schemas.wazuh import WazuhRuleInfo, WazuhAgentInfo

                        # Convert to stream format
                        stream_alert = WazuhAlertStream(
                            id=mapped_alert.get('id', ''),
                            timestamp=datetime.fromisoformat(mapped_alert.get('timestamp', datetime.utcnow().isoformat())),
                            source='wazuh',
                            severity=SeverityLevel(severity.lower()) if severity.lower() in ['critical', 'high', 'medium', 'low', 'info'] else SeverityLevel.MEDIUM,
                            event_type=mapped_alert.get('event_type', 'unknown'),
                            title=mapped_alert.get('title', 'Wazuh Alert'),
                            rule=WazuhRuleInfo(**mapped_alert.get('rule', {})),
                            agent=WazuhAgentInfo(**mapped_alert.get('agent', {})),
                            full_log=mapped_alert.get('full_log'),
                            location=mapped_alert.get('location'),
                            source_ip=mapped_alert.get('source_ip'),
                            dest_ip=mapped_alert.get('dest_ip'),
                            username=mapped_alert.get('username'),
                            iocs=mapped_alert.get('iocs', []),
                            analyzed=True
                        )

                        await stream_service.stream_alert(stream_alert)
                    except Exception as stream_error:
                        logger.debug(f"Failed to send alert to stream (non-critical): {stream_error}")

                # Log critical/high alerts immediately
                if severity in ['critical', 'high']:
                    logger.warning(
                        f"Published {severity.upper()} alert: {mapped_alert['id']} - "
                        f"{mapped_alert.get('title', 'Unknown')}"
                    )

            except Exception as e:
                logger.error(
                    f"Error processing event {event.get('id', 'unknown')}: {e}",
                    exc_info=True
                )
                self.total_errors += 1
                continue

        return published_count

    def _severity_to_queue(self, severity: str) -> str:
        """
        Map severity to queue priority

        Args:
            severity: Alert severity

        Returns:
            Queue priority name
        """
        mapping = {
            'critical': 'critical',
            'high': 'high',
            'medium': 'medium',
            'low': 'low'
        }
        return mapping.get(severity.lower(), 'medium')

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get receiver statistics

        Returns:
            Statistics dictionary
        """
        return {
            'is_running': self.is_running,
            'enabled': self.enabled,
            'poll_interval': self.poll_interval,
            'batch_size': self.batch_size,
            'last_poll_time': self.last_poll_time.isoformat() if self.last_poll_time else None,
            'total_events_received': self.total_events_received,
            'total_alerts_published': self.total_alerts_published,
            'total_errors': self.total_errors,
            'success_rate': (
                self.total_alerts_published / self.total_events_received * 100
                if self.total_events_received > 0 else 0
            )
        }

    def reset_statistics(self):
        """Reset statistics counters"""
        self.total_events_received = 0
        self.total_alerts_published = 0
        self.total_errors = 0
        logger.info("Statistics reset")


# Singleton instance
_wazuh_receiver: Optional[WazuhLogReceiver] = None


def get_wazuh_receiver() -> Optional[WazuhLogReceiver]:
    """Get Wazuh receiver singleton"""
    global _wazuh_receiver
    return _wazuh_receiver


def init_wazuh_receiver(
    poll_interval: int = 30,
    batch_size: int = 100,
    lookback_minutes: int = 5,
    enabled: bool = True
) -> WazuhLogReceiver:
    """
    Initialize Wazuh receiver singleton

    Args:
        poll_interval: Seconds between polling cycles
        batch_size: Maximum events to fetch per poll
        lookback_minutes: Minutes to look back for initial fetch
        enabled: Whether receiver is enabled

    Returns:
        WazuhLogReceiver instance
    """
    global _wazuh_receiver
    _wazuh_receiver = WazuhLogReceiver(
        poll_interval=poll_interval,
        batch_size=batch_size,
        lookback_minutes=lookback_minutes,
        enabled=enabled
    )
    return _wazuh_receiver


async def start_wazuh_receiver():
    """Start the Wazuh receiver service"""
    receiver = get_wazuh_receiver()
    if receiver:
        await receiver.start()


async def stop_wazuh_receiver():
    """Stop the Wazuh receiver service"""
    receiver = get_wazuh_receiver()
    if receiver:
        await receiver.stop()
