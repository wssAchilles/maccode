# Stream Reliability Runbook

## Scope

- Gateway order stream consumer group (`REDIS_ORDER_EVENTS_*`)
- Strategy market stream consumer group (`MARKET_STREAM_*`)
- Redis Stream reclaim + poison isolation

## Fast Triage (5 minutes)

1. Check gateway readiness: `GET /ready`
2. Check strategy readiness: `GET /ready`
3. Check backlog metrics:
   - Gateway: `order_stream_pending`, `order_stream_lag`, `order_stream_reclaim_failures`
   - Strategy: `market_stream_pending`, `market_stream_lag`, `market_stream_reclaim_failures`
4. Check poison counters:
   - Gateway: `order_stream_poisoned_events`
   - Strategy: `market_stream_poisoned`
5. Check last ingest errors:
   - Gateway: `last_order_ingest_error`
   - Strategy: `last_error`

## Failure Modes

### 1) Backlog keeps growing

Signals:
- `order_stream_pending` or `market_stream_pending` continuously rises
- `lag` rises and stays above warn threshold

Actions:
1. Increase consumer capacity (`cloud_run_gateway.max_instance_count`, `cloud_run_strategy.max_instance_count`)
2. Increase read batch size (`*_READ_BATCH_SIZE`) in small steps
3. Confirm Redis latency and connection stability
4. If lag remains high, reduce upstream publish rate temporarily

### 2) Reclaim loop fails repeatedly

Signals:
- `*_reclaim_failures_total` increments quickly
- readiness turns `false` with stream-related reason

Actions:
1. Validate consumer group/key configuration and Redis ACL
2. Validate reclaim params (`*_RECLAIM_IDLE_MS`, `*_RECLAIM_BATCH_SIZE`, `*_RECLAIM_INTERVAL_MS`)
3. Temporarily set `*_RECLAIM_ENABLED=false` only for emergency rollback
4. Re-enable reclaim after root cause is fixed

### 3) Poison events spike

Signals:
- `*_poisoned_events_total` increases
- same payload pattern appears in poison stream

Actions:
1. Inspect poison stream payloads for malformed fields
2. Check delivery attempts and source producer behavior
3. Fix producer/consumer contract mismatch
4. Replay safe entries manually after fix (from poison stream)

## Safe Defaults (Production)

- Reclaim enabled: `true`
- Reclaim interval: `5000ms`
- Reclaim idle: `30000ms`
- Max delivery attempts before poison: `8`
- Pending/Lag warn thresholds: `2000`

## Rollback Guidance

- Prefer config rollback over code rollback first
- Keep poison isolation enabled during rollback
- Never delete pending entries directly in Redis without snapshot
