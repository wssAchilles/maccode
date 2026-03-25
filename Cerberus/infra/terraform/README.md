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
terraform plan
terraform apply
```

## Notes

- `terraform.tfvars` contains secrets and must not be committed.
- This stack targets `Cloud Run (gateway/strategy/matching) + external Upstash/Supabase`.
- Frontend is hosted on Firebase Hosting (not provisioned by this Terraform module).
- Cloud Run services use image URIs from `container_images`.
- Terraform creates dedicated runtime service accounts and grants `roles/secretmanager.secretAccessor` for secret-backed env vars.
- Gateway exchange credentials (`BINANCE_API_KEY/BINANCE_API_SECRET/ALPACA_API_KEY/ALPACA_API_SECRET`) are managed via Secret Manager and injected at runtime.
- Strategy service receives `MATCHING_GRPC_TARGET` from Terraform (`cloud_run_matching_url`) so matching gRPC can be wired without manual env edits.
- Gateway market events are published to Redis Stream (`redis_market_events_stream_key`) with optional legacy Pub/Sub dual-write.
- Strategy market ingestion uses Redis Stream consumer group (`market_stream_consumer_group`) with optional Pub/Sub fallback.
- Matching capacity tunables are exposed (`matching_execution_stream_limit`, `matching_submit_latency_window_size`).
- Matching gRPC thread/CQ tuning is exposed (`matching_grpc_max_pollers`, `matching_grpc_min_pollers`, `matching_grpc_num_cqs`).
- Cloud Run runtime/capacity is parameterized per service:
  - `cloud_run_gateway`, `cloud_run_strategy`, `cloud_run_matching`
  - controls min/max instances, concurrency, timeout, CPU, memory, `cpu_idle`, `startup_cpu_boost`
- Gateway internal service auth can be controlled by Terraform:
  - `strategy_internal_auth_enabled`
  - `strategy_internal_auth_token_ttl_seconds`
  - `strategy_internal_auth_metadata_identity_url`
