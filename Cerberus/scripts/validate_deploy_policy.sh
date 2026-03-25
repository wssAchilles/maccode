#!/usr/bin/env bash
set -euo pipefail

require_non_empty() {
  local key="$1"
  local value="${!key:-}"
  if [[ -z "${value}" ]]; then
    echo "missing required deploy input: ${key}" >&2
    exit 1
  fi
}

require_boolean() {
  local key="$1"
  local value="${!key:-}"
  if [[ "${value}" != "true" && "${value}" != "false" ]]; then
    echo "invalid boolean for ${key}: ${value}" >&2
    exit 1
  fi
}

require_value() {
  local key="$1"
  local expected="$2"
  local actual="${!key:-}"
  if [[ "${actual}" != "${expected}" ]]; then
    echo "policy mismatch: ${key} must be '${expected}', got '${actual}'" >&2
    exit 1
  fi
}

validate_required_inputs() {
  local -a required_keys=(
    GRB_LICENSEID
    GRB_WLSACCESSID
    GRB_WLSSECRET
    UPSTASH_REDIS_URL
    UPSTASH_REDIS_REST_URL
    UPSTASH_REDIS_REST_TOKEN
    SUPABASE_PROJECT_URL
    SUPABASE_ANON_KEY
    SUPABASE_SERVICE_ROLE_KEY
    SUPABASE_DB_URL
    FIREBASE_API_KEY
    BINANCE_API_KEY
    BINANCE_API_SECRET
    ALPACA_API_KEY
    ALPACA_API_SECRET
    JWT_HS256_SECRET
    CORS_ALLOW_ORIGINS
    DEPLOY_ENV
  )

  local key
  for key in "${required_keys[@]}"; do
    require_non_empty "${key}"
  done
}

validate_policy_booleans() {
  local -a boolean_keys=(
    FIREBASE_AUTH_REQUIRED
    INTERNAL_SERVICES_INGRESS
    STRATEGY_PUBLIC_ACCESS
    MATCHING_PUBLIC_ACCESS
    JWT_AUTH_REQUIRE_IN_PRODUCTION
  )

  local key
  for key in "${boolean_keys[@]}"; do
    require_boolean "${key}"
  done
}

validate_service_exposure_policy() {
  require_value "INTERNAL_SERVICES_INGRESS" "true"
  require_value "STRATEGY_PUBLIC_ACCESS" "false"
  require_value "MATCHING_PUBLIC_ACCESS" "false"
}

validate_auth_policy() {
  require_value "FIREBASE_AUTH_REQUIRED" "true"
  local deploy_env
  deploy_env="$(echo "${DEPLOY_ENV}" | tr '[:upper:]' '[:lower:]')"
  if [[ "${deploy_env}" == "production" ]]; then
    require_value "JWT_AUTH_REQUIRE_IN_PRODUCTION" "true"
    if [[ "${CORS_ALLOW_ORIGINS}" == "*" ]]; then
      echo "policy mismatch: CORS_ALLOW_ORIGINS cannot be '*' in production" >&2
      exit 1
    fi
  fi
}

main() {
  validate_required_inputs
  validate_policy_booleans
  validate_service_exposure_policy
  validate_auth_policy
  echo "deploy policy validation passed"
}

main "$@"
