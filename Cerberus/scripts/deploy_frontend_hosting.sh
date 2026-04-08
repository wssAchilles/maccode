#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FRONTEND_DIR="${ROOT_DIR}/apps/frontend"

PROJECT_ID="${PROJECT_ID:-cerberus-9d94f}"
REGION="${REGION:-asia-east2}"
FIREBASE_APP_ID="${FIREBASE_APP_ID:-1:836238907711:web:c3fc58bfbd45d370c51b8a}"
HOSTING_URL="${HOSTING_URL:-https://${PROJECT_ID}.web.app}"
RUN_POST_DEPLOY_GATES="${RUN_POST_DEPLOY_GATES:-true}"
SKIP_BUNDLE_BUDGET="${SKIP_BUNDLE_BUDGET:-false}"

if ! command -v firebase >/dev/null 2>&1; then
  echo "firebase CLI is required" >&2
  exit 1
fi

if ! command -v gcloud >/dev/null 2>&1; then
  echo "gcloud CLI is required" >&2
  exit 1
fi

echo "resolving Firebase WEB sdk config for ${PROJECT_ID}"
SDK_JSON="$(firebase apps:sdkconfig WEB "${FIREBASE_APP_ID}" --project "${PROJECT_ID}")"

extract_json_field() {
  local field="$1"
  printf '%s' "${SDK_JSON}" | node -e "const fs=require('fs'); const data=JSON.parse(fs.readFileSync(0,'utf8')); const value=data['${field}']; if (value === undefined || value === null) process.exit(1); process.stdout.write(String(value));"
}

API_KEY="$(extract_json_field apiKey)"
AUTH_DOMAIN="$(extract_json_field authDomain)"
PROJECT_ID_FROM_APP="$(extract_json_field projectId)"
STORAGE_BUCKET="$(extract_json_field storageBucket)"
MESSAGING_SENDER_ID="$(extract_json_field messagingSenderId)"
APP_ID="$(extract_json_field appId)"

GATEWAY_URL="${VITE_GATEWAY_BASE:-$(gcloud run services describe cerberus-gateway --region "${REGION}" --project "${PROJECT_ID}" --format='value(status.url)')}"
STRATEGY_URL="${VITE_STRATEGY_BASE:-$(gcloud run services describe cerberus-strategy --region "${REGION}" --project "${PROJECT_ID}" --format='value(status.url)')}"

echo "building frontend against cloud endpoints"
(
  cd "${FRONTEND_DIR}"
  VITE_GATEWAY_BASE="${GATEWAY_URL}" \
  VITE_STRATEGY_BASE="${STRATEGY_URL}" \
  VITE_PUBLIC_APP_URL="${HOSTING_URL}" \
  VITE_AUTH_REQUIRED="true" \
  VITE_FIREBASE_API_KEY="${API_KEY}" \
  VITE_FIREBASE_AUTH_DOMAIN="${AUTH_DOMAIN}" \
  VITE_FIREBASE_PROJECT_ID="${PROJECT_ID_FROM_APP}" \
  VITE_FIREBASE_STORAGE_BUCKET="${STORAGE_BUCKET}" \
  VITE_FIREBASE_MESSAGING_SENDER_ID="${MESSAGING_SENDER_ID}" \
  VITE_FIREBASE_APP_ID="${APP_ID}" \
  npm run build

  if [[ "${SKIP_BUNDLE_BUDGET}" == "true" ]]; then
    echo "skipping bundle budget gate"
  else
    npm run check:bundle-budget
  fi
)

echo "deploying frontend to Firebase Hosting"
(
  cd "${ROOT_DIR}"
  firebase deploy --project "${PROJECT_ID}" --only hosting --non-interactive
)

echo "validating deployed frontend"
"${ROOT_DIR}/scripts/validate_frontend_hosting.sh" "${HOSTING_URL}"

if [[ "${RUN_POST_DEPLOY_GATES}" == "true" ]]; then
  echo "running deploy lighthouse gate against ${HOSTING_URL}"
  (
    cd "${FRONTEND_DIR}"
    LHCI_COLLECT_URL="${HOSTING_URL}" npm run lighthouse:gate
  )

  if [[ -n "${E2E_AUTH_EMAIL:-}" && -n "${E2E_AUTH_PASSWORD:-}" ]]; then
    echo "running deployed e2e gate against ${HOSTING_URL}"
    (
      cd "${FRONTEND_DIR}"
      E2E_BASE_URL="${HOSTING_URL}" \
      E2E_GATE_MODE="true" \
      E2E_USE_DEPLOYED="true" \
      E2E_AUTH_EMAIL="${E2E_AUTH_EMAIL}" \
      E2E_AUTH_PASSWORD="${E2E_AUTH_PASSWORD}" \
      npm run test:e2e:gate
    )
  else
    echo "skipping deployed e2e gate because E2E_AUTH_EMAIL / E2E_AUTH_PASSWORD are not set"
  fi
fi

printf '\nfrontend_url=%s\n' "${HOSTING_URL}"
printf 'gateway_url=%s\n' "${GATEWAY_URL}"
printf 'strategy_url=%s\n' "${STRATEGY_URL}"
