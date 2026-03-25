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
