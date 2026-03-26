# Terraform (dev environment)

## Prerequisites

- Billing enabled on project `cerberus-9d94f`
- `gcloud auth application-default login`
- Terraform >= 1.6

## Usage

```bash
cd infra/terraform
cp terraform.tfvars.example terraform.tfvars
terraform init
terraform fmt -check
terraform validate
terraform plan -var-file=environments/dev.tfvars -var-file=terraform.tfvars
terraform apply -var-file=environments/dev.tfvars -var-file=terraform.tfvars
```

Environment profile templates are under `infra/terraform/environments/`:

- `dev.tfvars`
- `staging.tfvars`
- `prod.tfvars`

Use them as base overlays with your secret-bearing `terraform.tfvars`.

## Notes

- `terraform.tfvars` contains secrets and must not be committed.
- This stack targets `Cloud Run (gateway/strategy/matching) + external Upstash/Supabase`.
- Frontend is hosted on Firebase Hosting (not provisioned by this Terraform module).
- Cloud Run services use image URIs from `container_images`.
- Terraform creates dedicated runtime service accounts and grants `roles/secretmanager.secretAccessor` for secret-backed env vars.
- Terraform policy guardrails fail `plan/apply` when required secret variables are empty.
- Production guardrails enforce stream-first mode (`market_stream_legacy_pubsub_fallback=false`, `redis_market_events_publish_legacy_pubsub=false`, `redis_order_events_legacy_pubsub_fallback=false`).
- Strategy event publisher env is Terraform-managed (`EVENT_STREAM_ENABLED`, `EVENT_STREAM_KEY`, `EVENT_STREAM_PUBLISH_LEGACY_PUBSUB`), with legacy publish tied to `redis_order_events_legacy_pubsub_fallback`.
- Strategy event stream retention knob is Terraform-managed via `strategy_event_stream_maxlen` -> `EVENT_STREAM_MAXLEN`.
- Gateway exchange credentials (`BINANCE_API_KEY/BINANCE_API_SECRET/ALPACA_API_KEY/ALPACA_API_SECRET`) are managed via Secret Manager and injected at runtime.
- Strategy service receives `MATCHING_GRPC_TARGET` from Terraform (`cloud_run_matching_url`) so matching gRPC can be wired without manual env edits.
- Gateway market events are published to Redis Stream (`redis_market_events_stream_key`) with optional legacy Pub/Sub dual-write.
- Strategy market ingestion uses Redis Stream consumer group (`market_stream_consumer_group`) with optional Pub/Sub fallback.
- Strategy market stream reliability knobs are exposed for reclaim/poison/backlog:
  - `market_stream_reclaim_enabled`, `market_stream_reclaim_interval_ms`, `market_stream_reclaim_idle_ms`, `market_stream_reclaim_batch_size`
  - `market_stream_max_delivery_attempts`, `market_stream_pending_warn_threshold`, `market_stream_lag_warn_threshold`
  - `market_stream_poison_stream_key`, `market_stream_poison_stream_maxlen`
- Gateway order stream reliability knobs are exposed for reclaim/poison/backlog:
  - `redis_order_events_reclaim_enabled`, `redis_order_events_reclaim_interval_ms`, `redis_order_events_reclaim_idle_ms`, `redis_order_events_reclaim_batch_size`
  - `redis_order_events_max_delivery_attempts`, `redis_order_events_pending_warn_threshold`, `redis_order_events_lag_warn_threshold`
  - `redis_order_events_poison_stream_key`, `redis_order_events_poison_stream_maxlen`
  - `redis_order_events_legacy_pubsub_fallback` (controls stream failure fallback to legacy Pub/Sub)
- Matching capacity tunables are exposed:
  - `matching_execution_stream_limit`, `matching_submit_latency_window_size`
  - `matching_max_inflight_requests`, `matching_inflight_acquire_timeout_ms`, `matching_backpressure_retry_sleep_ms`
- Matching gRPC thread/CQ tuning is exposed (`matching_grpc_max_pollers`, `matching_grpc_min_pollers`, `matching_grpc_num_cqs`).
- Cloud Run runtime/capacity is parameterized per service:
  - `cloud_run_gateway`, `cloud_run_strategy`, `cloud_run_matching`
  - controls min/max instances, concurrency, timeout, CPU, memory, `cpu_idle`, `startup_cpu_boost`
- Gateway internal service auth can be controlled by Terraform:
  - `strategy_internal_auth_enabled`
  - `strategy_internal_auth_token_ttl_seconds`
  - `strategy_internal_auth_metadata_identity_url`
- Gateway strategy upstream resilience can be tuned:
  - `strategy_upstream_timeout_ms`, `strategy_upstream_health_timeout_ms`
  - `strategy_upstream_max_inflight`, `strategy_upstream_queue_timeout_ms`
  - `strategy_upstream_circuit_enabled`, `strategy_upstream_circuit_failure_threshold`, `strategy_upstream_circuit_open_ms`
  - `strategy_summary_cache_ttl_ms`, `strategy_summary_batch_window_ms`
