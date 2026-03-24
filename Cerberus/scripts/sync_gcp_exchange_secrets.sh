#!/usr/bin/env bash
set -euo pipefail

PROJECT_ID="${1:-$(gcloud config get-value project 2>/dev/null || true)}"
REGION="${2:-asia-east2}"
GATEWAY_SERVICE="${GATEWAY_SERVICE:-cerberus-gateway}"
STRATEGY_SERVICE="${STRATEGY_SERVICE:-cerberus-strategy}"

if [[ -z "${PROJECT_ID}" ]]; then
  echo "PROJECT_ID is required (arg1 or active gcloud project)." >&2
  exit 1
fi

BINANCE_API_KEY="${BINANCE_API_KEY:-}"
BINANCE_API_SECRET="${BINANCE_API_SECRET:-}"
ALPACA_API_KEY="${ALPACA_API_KEY:-}"
ALPACA_API_SECRET="${ALPACA_API_SECRET:-}"

SECRET_NAMES=(
  "cerberus-binance-api-key"
  "cerberus-binance-api-secret"
  "cerberus-alpaca-api-key"
  "cerberus-alpaca-api-secret"
)
SECRET_VALUES=(
  "${BINANCE_API_KEY}"
  "${BINANCE_API_SECRET}"
  "${ALPACA_API_KEY}"
  "${ALPACA_API_SECRET}"
)

ensure_secret() {
  local name="$1"
  if ! gcloud secrets describe "$name" --project="$PROJECT_ID" >/dev/null 2>&1; then
    gcloud secrets create "$name" --project="$PROJECT_ID" --replication-policy=automatic >/dev/null
    echo "created secret: $name"
  fi
}

add_secret_version() {
  local name="$1"
  local value="$2"
  printf '%s' "$value" | gcloud secrets versions add "$name" --project="$PROJECT_ID" --data-file=- >/dev/null
  echo "added version: $name"
}

grant_accessor() {
  local name="$1"
  local sa="$2"
  gcloud secrets add-iam-policy-binding "$name" \
    --project="$PROJECT_ID" \
    --member="serviceAccount:${sa}" \
    --role="roles/secretmanager.secretAccessor" >/dev/null
}

declare -a UPDATED_SECRETS=()

for i in "${!SECRET_NAMES[@]}"; do
  secret_name="${SECRET_NAMES[$i]}"
  value="${SECRET_VALUES[$i]}"
  if [[ -z "${value}" ]]; then
    echo "skip empty secret value: ${secret_name}"
    continue
  fi
  ensure_secret "${secret_name}"
  add_secret_version "${secret_name}" "${value}"
  UPDATED_SECRETS+=("${secret_name}")
done

if [[ "${#UPDATED_SECRETS[@]}" -eq 0 ]]; then
  echo "no non-empty exchange secrets provided; nothing to update"
  exit 0
fi

for service in "${GATEWAY_SERVICE}" "${STRATEGY_SERVICE}"; do
  sa="$(gcloud run services describe "${service}" --project="${PROJECT_ID}" --region="${REGION}" --format='value(spec.template.spec.serviceAccountName)' 2>/dev/null || true)"
  if [[ -z "${sa}" ]]; then
    echo "skip IAM binding, service not found in ${REGION}: ${service}"
    continue
  fi
  for secret_name in "${UPDATED_SECRETS[@]}"; do
    grant_accessor "${secret_name}" "${sa}"
  done
  echo "granted secretAccessor to ${service} runtime SA: ${sa}"
done

echo "exchange secret sync complete for project ${PROJECT_ID}"
