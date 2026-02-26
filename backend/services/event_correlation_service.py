"""Event correlation service.

Groups related security events into incidents using:
- Entity-based correlation (IP, user, hostname)
- Time-based correlation (within N minutes)
- Similarity-based correlation (message, category, severity)
- Rule-based correlation (custom conditions)
"""

import asyncio
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional, Set
from collections import defaultdict
import logging

from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from models.correlation_rule import CorrelationRule
from models.correlated_event import CorrelatedEvent
from models.event_similarity import EventSimilarity
from core.logger import get_logger

logger = get_logger(__name__)


class EventCorrelationService:
    """Service for correlating related events into incidents."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def correlate_events(
        self,
        events: List[Dict[str, Any]],
        rule_ids: Optional[List[str]] = None
    ) -> List[CorrelatedEvent]:
        """
        Correlate a batch of events into incidents.

        Args:
            events: List of raw events/alerts
            rule_ids: Optional list of specific rules to apply (default: all enabled rules)

        Returns:
            List of correlated events (incidents)
        """
        logger.info(f"Starting correlation for {len(events)} events")

        # 1. Fetch applicable rules
        rules = await self._get_rules(rule_ids)
        logger.info(f"Applying {len(rules)} correlation rules")

        # 2. Extract entities from events
        events_with_entities = await self._extract_entities(events)

        # 3. Group events by time windows
        time_groups = await self._group_by_time(events_with_entities)

        # 4. Apply correlation rules
        correlated_events = []
        for rule in rules:
            rule_results = await self._apply_rule(rule, time_groups)
            correlated_events.extend(rule_results)

        # 5. Merge overlapping correlations
        merged_events = await self._merge_correlations(correlated_events)

        # 6. Persist to database
        for event in merged_events:
            await self.db.merge(event)
        await self.db.commit()

        logger.info(f"Generated {len(merged_events)} correlated incidents")
        return merged_events

    async def _get_rules(self, rule_ids: Optional[List[str]] = None) -> List[CorrelationRule]:
        """Fetch correlation rules from database."""
        query = select(CorrelationRule).where(CorrelationRule.enabled == True)

        if rule_ids:
            query = query.where(CorrelationRule.id.in_(rule_ids))
        else:
            query = query.order_by(CorrelationRule.priority.desc())

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def _extract_entities(
        self,
        events: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Extract entities (IPs, users, hostnames) from events.

        Returns:
            List of events with added 'entities' field
        """
        enriched_events = []

        for event in events:
            entities = {
                "ip_addresses": self._extract_ips(event),
                "usernames": self._extract_usernames(event),
                "hostnames": self._extract_hostnames(event),
                "domains": self._extract_domains(event),
            }

            event["entities"] = entities
            enriched_events.append(event)

        return enriched_events

    def _extract_ips(self, event: Dict[str, Any]) -> Set[str]:
        """Extract IP addresses from event."""
        ips = set()

        # Common IP fields
        for field in ["source_ip", "dest_ip", "ip_address", "src_ip", "dst_ip"]:
            if field in event and event[field]:
                ips.add(event[field])

        # Check nested fields
        if "network" in event:
            for ip in event["network"].get("source_ips", []):
                ips.add(ip)
            for ip in event["network"].get("dest_ips", []):
                ips.add(ip)

        return ips

    def _extract_usernames(self, event: Dict[str, Any]) -> Set[str]:
        """Extract usernames from event."""
        users = set()

        for field in ["username", "user", "actor", "account"]:
            if field in event and event[field]:
                users.add(str(event[field]))

        return users

    def _extract_hostnames(self, event: Dict[str, Any]) -> Set[str]:
        """Extract hostnames from event."""
        hosts = set()

        for field in ["hostname", "host", "device", "computer"]:
            if field in event and event[field]:
                hosts.add(str(event[field]))

        return hosts

    def _extract_domains(self, event: Dict[str, Any]) -> Set[str]:
        """Extract domain names from event."""
        domains = set()

        for field in ["domain", "fqdn", "dns_query"]:
            if field in event and event[field]:
                domains.add(str(event[field]))

        return domains

    async def _group_by_time(
        self,
        events: List[Dict[str, Any]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Group events into time buckets.

        Returns:
            Dict mapping time_bucket -> list of events
        """
        time_groups = defaultdict(list)

        for event in events:
            # Parse timestamp
            timestamp_str = event.get("timestamp") or event.get("created_at")
            if not timestamp_str:
                continue

            try:
                timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                continue

            # Create 5-minute time bucket
            bucket = timestamp.replace(second=0, microsecond=0)
            bucket = bucket.replace(minute=(bucket.minute // 5) * 5)
            bucket_key = bucket.isoformat()

            time_groups[bucket_key].append(event)

        return dict(time_groups)

    async def _apply_rule(
        self,
        rule: CorrelationRule,
        time_groups: Dict[str, List[Dict[str, Any]]]
    ) -> List[CorrelatedEvent]:
        """
        Apply a single correlation rule to time-grouped events.

        Returns:
            List of correlated events matching this rule
        """
        correlated = []
        window_seconds = rule.time_window_seconds
        entity_types = rule.entity_types

        # Expand time groups to include overlapping windows
        expanded_groups = self._expand_time_windows(time_groups, window_seconds)

        for events in expanded_groups.values():
            # Group by common entities
            entity_groups = await self._group_by_entities(events, entity_types)

            for entity_key, group_events in entity_groups.items():
                # Check minimum event count
                if len(group_events) < 2:
                    continue

                # Check similarity threshold
                similarity = await self._calculate_group_similarity(group_events)
                if similarity < rule.min_similarity:
                    continue

                # Check custom conditions
                if not await self._check_conditions(group_events, rule.conditions):
                    continue

                # Create correlated event
                correlated_event = await self._create_correlated_event(
                    rule, group_events, similarity
                )
                correlated.append(correlated_event)

        return correlated

    def _expand_time_windows(
        self,
        time_groups: Dict[str, List[Dict[str, Any]]],
        window_seconds: int
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Expand time groups to include events within sliding windows.

        For example, with window=10min and bucket=5min:
        - Bucket 10:00 should include events from 09:50-10:05
        """
        expanded = defaultdict(list)

        # Get sorted time buckets
        sorted_buckets = sorted(time_groups.keys())

        for i, current_bucket in enumerate(sorted_buckets):
            current_events = time_groups[current_bucket]
            expanded[current_bucket].extend(current_events)

            # Include previous buckets within window
            current_time = datetime.fromisoformat(current_bucket)
            for j in range(i - 1, max(0, i - 3), -1):
                prev_bucket = sorted_buckets[j]
                prev_time = datetime.fromisoformat(prev_bucket)
                time_diff = (current_time - prev_time).total_seconds()

                if time_diff <= window_seconds:
                    expanded[current_bucket].extend(time_groups[prev_bucket])
                else:
                    break

        return dict(expanded)

    async def _group_by_entities(
        self,
        events: List[Dict[str, Any]],
        entity_types: Dict[str, bool]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Group events by common entities.

        Returns:
            Dict mapping entity_key -> list of events
        """
        entity_groups = defaultdict(list)

        for event in events:
            entity_key = self._compute_entity_key(event, entity_types)
            if entity_key:
                entity_groups[entity_key].append(event)

        return dict(entity_groups)

    def _compute_entity_key(
        self,
        event: Dict[str, Any],
        entity_types: Dict[str, bool]
    ) -> Optional[str]:
        """Compute a key for grouping events by entities."""
        key_parts = []

        entities = event.get("entities", {})

        if entity_types.get("ip_address") and entities.get("ip_addresses"):
            key_parts.append(f"ips:{','.join(sorted(entities['ip_addresses']))}")

        if entity_types.get("username") and entities.get("usernames"):
            key_parts.append(f"users:{','.join(sorted(entities['usernames']))}")

        if entity_types.get("hostname") and entities.get("hostnames"):
            key_parts.append(f"hosts:{','.join(sorted(entities['hostnames']))}")

        return "|".join(key_parts) if key_parts else None

    async def _calculate_group_similarity(
        self,
        events: List[Dict[str, Any]]
    ) -> float:
        """
        Calculate similarity score for a group of events.

        Uses multiple signals:
        - Message similarity (Jaccard on tokens)
        - Category/attack type match
        - Severity proximity
        """
        if len(events) < 2:
            return 1.0

        # 1. Message similarity (Jaccard)
        message_similarity = await self._jaccard_similarity_messages(events)

        # 2. Category similarity
        category_similarity = await self._category_match_score(events)

        # 3. Severity proximity
        severity_similarity = await self._severity_proximity_score(events)

        # Weighted average
        weights = {"message": 0.5, "category": 0.3, "severity": 0.2}
        total_similarity = (
            weights["message"] * message_similarity +
            weights["category"] * category_similarity +
            weights["severity"] * severity_similarity
        )

        return min(1.0, max(0.0, total_similarity))

    async def _jaccard_similarity_messages(
        self,
        events: List[Dict[str, Any]]
    ) -> float:
        """Calculate Jaccard similarity between event messages."""
        messages = [
            set(str(e.get("message", "")).lower().split())
            for e in events
        ]

        if not messages or not any(messages):
            return 0.0

        # Calculate pairwise similarities
        similarities = []
        for i in range(len(messages)):
            for j in range(i + 1, len(messages)):
                intersection = messages[i] & messages[j]
                union = messages[i] | messages[j]
                if union:
                    jaccard = len(intersection) / len(union)
                    similarities.append(jaccard)

        return sum(similarities) / len(similarities) if similarities else 0.0

    async def _category_match_score(
        self,
        events: List[Dict[str, Any]]
    ) -> float:
        """Calculate category match score (1.0 if all same, 0.0 if all different)."""
        categories = [e.get("category") or e.get("attack_type", "unknown") for e in events]

        if len(set(categories)) == 1:
            return 1.0
        elif len(set(categories)) == len(categories):
            return 0.0
        else:
            # Partial match
            unique_ratio = len(set(categories)) / len(categories)
            return 1.0 - unique_ratio

    async def _severity_proximity_score(
        self,
        events: List[Dict[str, Any]]
    ) -> float:
        """Calculate severity proximity score."""
        severity_map = {"critical": 4, "high": 3, "medium": 2, "low": 1, "info": 0}
        severities = [
            severity_map.get(e.get("severity", "low").lower(), 0)
            for e in events
        ]

        if not severities:
            return 0.0

        # Calculate standard deviation
        avg = sum(severities) / len(severities)
        variance = sum((s - avg) ** 2 for s in severities) / len(severities)

        # Convert to similarity (lower variance = higher similarity)
        max_variance = 4.0  # Maximum possible variance
        proximity = 1.0 - (variance / max_variance)

        return proximity

    async def _check_conditions(
        self,
        events: List[Dict[str, Any]],
        conditions: Optional[Dict[str, Any]]
    ) -> bool:
        """Check if events match custom conditions."""
        if not conditions:
            return True

        # Example conditions:
        # {
        #   "min_severity": "high",
        #   "category": ["malware", "phishing"],
        #   "min_event_count": 5
        # }

        # Check min event count
        min_count = conditions.get("min_event_count")
        if min_count and len(events) < min_count:
            return False

        # Check severity filter
        min_severity = conditions.get("min_severity")
        if min_severity:
            severity_map = {"critical": 4, "high": 3, "medium": 2, "low": 1, "info": 0}
            min_level = severity_map.get(min_severity.lower(), 0)

            for event in events:
                event_severity = severity_map.get(
                    event.get("severity", "low").lower(),
                    0
                )
                if event_severity < min_level:
                    return False

        # Check category filter
        allowed_categories = conditions.get("category")
        if allowed_categories:
            for event in events:
                event_category = event.get("category") or event.get("attack_type")
                if event_category not in allowed_categories:
                    return False

        return True

    async def _create_correlated_event(
        self,
        rule: CorrelationRule,
        events: List[Dict[str, Any]],
        similarity: float
    ) -> CorrelatedEvent:
        """Create a CorrelatedEvent from grouped events."""
        # Extract common entities
        common_entities = self._extract_common_entities(events)

        # Determine time range
        timestamps = [
            datetime.fromisoformat(e.get("timestamp", e.get("created_at", "")).replace("Z", "+00:00"))
            for e in events
            if e.get("timestamp") or e.get("created_at")
        ]

        if not timestamps:
            first_seen = last_seen = datetime.now(timezone.utc).isoformat()
        else:
            first_seen = min(timestamps).isoformat()
            last_seen = max(timestamps).isoformat()

        # Determine severity (use max)
        severity_map = {"critical": 4, "high": 3, "medium": 2, "low": 1, "info": 0}
        max_severity_level = max(
            [
                severity_map.get(e.get("severity", "low").lower(), 0)
                for e in events
            ]
        )
        severity = ["info", "low", "medium", "high", "critical"][max_severity_level]

        # Create correlated event
        import uuid
        correlated = CorrelatedEvent(
            id=str(uuid.uuid4()),
            rule_id=rule.id,
            title=f"Correlated: {len(events)} related events",
            description=f"Events correlated by rule: {rule.name}",
            severity=severity,
            attack_type=events[0].get("attack_type") if events else None,
            confidence_score=similarity,
            raw_event_ids=[e.get("id") for e in events if e.get("id")],
            raw_event_count=len(events),
            common_entities=common_entities,
            first_seen=first_seen,
            last_seen=last_seen,
            status="open",
            risk_score=50.0,  # TODO: Calculate based on severity + asset criticality
            created_at=datetime.now(timezone.utc).isoformat(),
        )

        return correlated

    def _extract_common_entities(
        self,
        events: List[Dict[str, Any]]
    ) -> Dict[str, List[str]]:
        """Extract entities common to all events."""
        all_ips = set()
        all_users = set()
        all_hosts = set()

        for event in events:
            entities = event.get("entities", {})
            all_ips.update(entities.get("ip_addresses", []))
            all_users.update(entities.get("usernames", []))
            all_hosts.update(entities.get("hostnames", []))

        return {
            "ip_addresses": list(all_ips),
            "usernames": list(all_users),
            "hostnames": list(all_hosts),
        }

    async def _merge_correlations(
        self,
        correlated_events: List[CorrelatedEvent]
    ) -> List[CorrelatedEvent]:
        """
        Merge overlapping correlated events.

        If two correlations share >50% of raw events, merge them.
        """
        if len(correlated_events) < 2:
            return correlated_events

        # Sort by raw event count (descending)
        correlated_events.sort(key=lambda e: e.raw_event_count, reverse=True)

        merged = []
        used_ids = set()

        for event in correlated_events:
            if event.id in used_ids:
                continue

            # Find overlapping events
            overlap_events = [event]
            overlap_ids = set(event.raw_event_ids)

            for other in correlated_events:
                if other.id == event.id or other.id in used_ids:
                    continue

                # Calculate overlap
                other_ids = set(other.raw_event_ids)
                intersection = overlap_ids & other_ids
                union = overlap_ids | other_ids

                if intersection and len(intersection) / len(union) > 0.5:
                    overlap_events.append(other)
                    overlap_ids.update(other_ids)
                    used_ids.add(other.id)

            # Merge overlapping events
            if len(overlap_events) > 1:
                merged_event = await self._merge_multiple_events(overlap_events)
                merged.append(merged_event)
            else:
                merged.append(event)

            used_ids.add(event.id)

        return merged

    async def _merge_multiple_events(
        self,
        events: List[CorrelatedEvent]
    ) -> CorrelatedEvent:
        """Merge multiple correlated events into one."""
        # Use the largest event as base
        base = max(events, key=lambda e: e.raw_event_count)

        # Aggregate data
        all_raw_ids = []
        all_entities = {
            "ip_addresses": set(),
            "usernames": set(),
            "hostnames": set(),
        }

        for event in events:
            all_raw_ids.extend(event.raw_event_ids)
            for key in all_entities:
                if event.common_entities and key in event.common_entities:
                    all_entities[key].update(event.common_entities[key])

        # Update base event
        base.raw_event_ids = list(set(all_raw_ids))
        base.raw_event_count = len(base.raw_event_ids)
        base.common_entities = {k: list(v) for k, v in all_entities.items()}
        base.title = f"Correlated: {base.raw_event_count} related events"

        # Update time range
        timestamps = [
            datetime.fromisoformat(ts)
            for ts in [base.first_seen, base.last_seen] +
            [e.first_seen for e in events if e.first_seen] +
            [e.last_seen for e in events if e.last_seen]
        ]
        base.first_seen = min(timestamps).isoformat()
        base.last_seen = max(timestamps).isoformat()

        return base


# Convenience function
async def correlate_events_batch(
    events: List[Dict[str, Any]],
    db: AsyncSession
) -> List[CorrelatedEvent]:
    """
    Correlate a batch of events.

    Convenience function that creates the service and runs correlation.
    """
    service = EventCorrelationService(db)
    return await service.correlate_events(events)
