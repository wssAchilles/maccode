#!/usr/bin/env bash
set -euo pipefail

is_true() {
  case "${1:-}" in
    1|true|TRUE|yes|YES|on|ON) return 0 ;;
    *) return 1 ;;
  esac
}

require_command() {
  local cmd="$1"
  if ! command -v "${cmd}" >/dev/null 2>&1; then
    echo "required command not found: ${cmd}" >&2
    exit 1
  fi
}

create_temp_yaml() {
  local prefix="$1"
  local base path
  base="$(mktemp "${TMPDIR:-/tmp}/${prefix}.XXXXXX")"
  path="${base}.yaml"
  mv "${base}" "${path}"
  printf '%s\n' "${path}"
}

CLEANUP_FILES=()

register_cleanup_file() {
  local file="$1"
  CLEANUP_FILES+=("${file}")
}

cleanup_registered_files() {
  local file
  for file in "${CLEANUP_FILES[@]:-}"; do
    [[ -n "${file}" ]] && rm -f "${file}" || true
  done
}

run_cmd() {
  if is_true "${DRY_RUN:-false}"; then
    printf '+'
    printf ' %q' "$@"
    printf '\n'
    return 0
  fi
  "$@"
}

gcloud_quiet_args() {
  if is_true "${GCLOUD_QUIET:-true}"; then
    printf '%s\n' "--quiet"
  fi
}

ensure_artifact_registry_repo() {
  local project_id="$1"
  local region="$2"
  local repository="$3"

  if is_true "${DRY_RUN:-false}"; then
    echo "[dry-run] ensure Artifact Registry repository ${repository} (${project_id}/${region})"
    return 0
  fi

  if gcloud artifacts repositories describe "${repository}" \
    --project="${project_id}" \
    --location="${region}" >/dev/null 2>&1; then
    return 0
  fi

  echo "creating Artifact Registry repository: ${repository}"
  gcloud artifacts repositories create "${repository}" \
    --project="${project_id}" \
    --location="${region}" \
    --repository-format=docker \
    --description="Cerberus container images" \
    $(gcloud_quiet_args)
}
