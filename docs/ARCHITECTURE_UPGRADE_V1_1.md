# SOC Architecture Upgrade v1.1 (P0 -> P1 -> P2)

## 1. Event Flow (P0)

Wazuh -> Webhook/Poller -> Event Bus -> Correlation -> Playbook DAG -> Notification Providers

Detailed path:
1. `POST /api/v1/wazuh/events/webhook` receives raw Wazuh event.
2. `services/wazuh_event_receiver.py` normalizes event and publishes `wazuh.alert.received`.
3. `services/message_broker/redis_broker.py` routes by priority with consumer group ack/nack.
4. Failed processing enters delayed retry and then DLQ.
5. `replay_dlq()` replays failed events to active streams.

## 2. Correlation DSL Example (P0)

```json
{
  "id": "rule_failed_login_spike",
  "name": "Failed login spike by host+ip",
  "enabled": true,
  "weight": 2.5,
  "aggregation": {
    "window_seconds": 600,
    "dimensions": ["source_ip", "agent_name", "username"]
  },
  "clause": {
    "operator": "AND",
    "conditions": [
      {"field": "event_type", "op": "in", "value": ["auth_failed", "login_failed"]},
      {"field": "severity", "op": "in", "value": ["high", "critical"]}
    ]
  },
  "threshold": {"min_count": 3, "min_score": 6.0}
}
```

## 3. Playbook DAG State Machine (P1)

Node states:
- `pending -> running -> success`
- `pending -> running -> failed -> rolling_back -> rolled_back`
- `pending -> waiting_approval -> running -> success`
- `pending -> skipped`

Branching:
- `on_success` edges execute next business nodes.
- `on_failure` edges execute compensation nodes.
- `rollback_node_id` executes explicit rollback action when failure occurs.

## 4. Before vs After

Before:
- Redis Streams used directly by multiple modules.
- Wazuh integration mainly polling path.
- Correlation based on basic similarity and fixed logic.
- Notifications tightly coupled in one service.

After:
- `MessageBroker` abstraction with Redis implementation, DLQ/retry/delay/replay.
- Wazuh webhook event-driven ingest added, polling kept as compatibility mode.
- DSL-based `RuleEngine` with window + dimensions + weighted scoring + logs.
- Pluginized notifications with dynamic provider registration.
- Tenant middleware and RBAC model/dependency scaffolding.

## 5. Frontend Optimization Recommendations (P1)

1. Prefer RSC for read-only heavy dashboard blocks.
2. Use virtual list for alerts/assets tables > 200 rows.
3. Split dashboard widgets into Suspense boundaries.
4. Merge adjacent API requests via backend aggregation endpoint.

Example snippets:

```tsx
// Suspense partitioning
<Suspense fallback={<WidgetSkeleton />}>
  <CriticalAlertsWidget />
</Suspense>
```

```tsx
// Virtualized list
<VirtualList items={rows} itemHeight={44} renderItem={(row) => <Row row={row} />} />
```

## 6. Migration Phases

Phase A (P0 baseline):
1. Deploy code with `MESSAGE_BROKER=redis`.
2. Start webhook endpoint and keep poller enabled.
3. Route new alerts through event bus.
4. Observe queue stats, DLQ and delayed queue metrics.

Phase B (P1 enhancement):
1. Enable notification plugin registry.
2. Enable RuleEngine DSL endpoint and shadow evaluation.
3. Introduce enhanced DAG orchestration semantics.

Phase C (P2 prep):
1. Run migration `v1_1_0_arch_upgrade`.
2. Inject tenant from middleware and propagate to writes.
3. Enable RBAC permission checks incrementally by endpoint.
4. Integrate AI analyzer adapter with production LLM provider.

## 7. Rollback Strategy

1. Disable webhook intake and return to poller-only mode.
2. Switch consumers to read old stream aliases if required.
3. Disable strict RBAC checks, keep role-level controls.
4. Rollback Alembic migration `v1_1_0_arch_upgrade`.
5. Replay DLQ after fix to avoid message loss.

