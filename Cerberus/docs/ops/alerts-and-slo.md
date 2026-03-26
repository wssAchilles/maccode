# Alerts And SLO Baseline

## Service SLO Targets

- Gateway request P95 latency: <= `800ms`
- Gateway synthetic throughput (deploy gate): >= `2 rps`
- Unit request cost: <= `0.01 USD` (configurable by environment)
- Stream backlog steady-state:
  - `order_stream_pending <= 2000`
  - `order_stream_lag <= 2000`
  - `market_stream_pending <= 2000`
  - `market_stream_lag <= 2000`

## Critical Alerts

1. `GatewayReadyFalse`
- Condition: `/ready` is not ready for 3 consecutive checks
- Severity: critical

2. `GatewayOrderStreamBacklogHigh`
- Condition: `cerberus_gateway_order_stream_pending > 2000` for 5 minutes
- Severity: warning -> critical after 15 minutes

3. `GatewayOrderStreamPoisonSpike`
- Condition: increase(`cerberus_gateway_order_stream_poisoned_events_total[10m]`) > 20
- Severity: warning

4. `StrategyMarketStreamBacklogHigh`
- Condition: `cerberus_strategy_market_stream_pending > 2000` for 5 minutes
- Severity: warning -> critical after 15 minutes

5. `StrategyMarketStreamPoisonSpike`
- Condition: increase(`cerberus_strategy_market_stream_poisoned_total[10m]`) > 20
- Severity: warning

## Observability Notes

- Readiness now includes stream lag/pending reasons.
- Reclaim failures are tracked independently from normal read failures.
- Poison stream keys are configurable and should be retained for forensic replay.
