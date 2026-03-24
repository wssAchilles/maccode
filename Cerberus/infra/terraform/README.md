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
- The generated GKE cluster is intended for matching engine and TimescaleDB workloads.
- Cloud Run services use image URIs from `container_images`.

