# Stage 1 Observability - Prometheus Metric Examples

## API

- `soc_api_requests_total{method,path,status,tenant_id}`
- `soc_api_request_duration_seconds_bucket{method,path,tenant_id,le}`

## Queue

- `soc_queue_consume_total{stream,consumer_group,result}`
- `soc_queue_processing_seconds_bucket{stream,consumer_group,le}`
- `soc_queue_lag{stream}`
- `soc_queue_retry_total{stream}`
- `soc_queue_dlq_total{stream}`

## Playbook

- `soc_playbook_runs_total{playbook_name,status,mode,tenant_id}`
- `soc_playbook_run_duration_seconds_bucket{playbook_name,tenant_id,le}`
- `soc_playbook_errors_total{playbook_name,error_type,tenant_id}`

## Correlation

- `soc_correlation_rule_hit_total{rule_id,tenant_id}`

## Errors

- `soc_exceptions_total{exception_type,path}`

## Query Examples

- API P95:
  `histogram_quantile(0.95, sum by (le) (rate(soc_api_request_duration_seconds_bucket[5m])))`
- Queue lag peak:
  `max by (stream) (soc_queue_lag)`
- Correlation top rules:
  `topk(10, sum by (rule_id) (increase(soc_correlation_rule_hit_total[1h])))`
