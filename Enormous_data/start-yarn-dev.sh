#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_PORT="${YARN_WEB_PORT:-5050}"
FRONTEND_PORT="${FRONTEND_PORT:-5173}"
BACKEND_HEALTH_URL="http://127.0.0.1:${BACKEND_PORT}/healthz"
FRONTEND_URL="http://127.0.0.1:${FRONTEND_PORT}/"
API_BASE_URL="http://127.0.0.1:${BACKEND_PORT}/api/v1"

cd "$ROOT_DIR"

frontend_pid=""

log() {
  printf '[yarn-dev] %s\n' "$*"
}

fail() {
  printf '[yarn-dev] ERROR: %s\n' "$*" >&2
  exit 1
}

terminate_process_tree() {
  local pid="$1"
  local child=""

  if [[ -z "$pid" ]] || ! kill -0 "$pid" 2>/dev/null; then
    return
  fi

  if command -v pgrep >/dev/null 2>&1; then
    for child in $(pgrep -P "$pid" 2>/dev/null || true); do
      terminate_process_tree "$child"
    done
  fi

  kill "$pid" 2>/dev/null || true
}

cleanup() {
  local status=$?
  trap - EXIT INT TERM HUP

  if [[ -n "$frontend_pid" ]] && kill -0 "$frontend_pid" 2>/dev/null; then
    log "Stopping frontend..."
    terminate_process_tree "$frontend_pid"
  fi

  wait "$frontend_pid" 2>/dev/null || true

  if [[ "${STOP_DOCKER_ON_EXIT:-0}" == "1" ]]; then
    log "Stopping yarn-lab Docker stack..."
    docker compose --profile yarn-lab down
  else
    log "YARN Docker stack is still running. Stop it with: docker compose --profile yarn-lab down"
  fi

  exit "$status"
}

trap cleanup EXIT INT TERM HUP

require_command() {
  local name="$1"
  command -v "$name" >/dev/null 2>&1 || fail "Missing command: ${name}"
}

require_free_port() {
  local port="$1"
  local label="$2"

  if ! command -v lsof >/dev/null 2>&1; then
    return
  fi

  local pids
  pids=$(lsof -tiTCP:"$port" -sTCP:LISTEN 2>/dev/null || true)

  if [[ -z "$pids" ]]; then
    return
  fi

  log "${label} port ${port} is occupied, killing: ${pids}"
  for pid in $pids; do
    terminate_process_tree "$pid"
  done

  sleep 1

  if lsof -nP -iTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1; then
    fail "${label} port ${port} could not be freed."
  fi
}

ensure_frontend_deps() {
  require_command npm

  local marker="frontend/node_modules/.package-lock.json"
  if [[ ! -f "$marker" || frontend/package.json -nt "$marker" || frontend/package-lock.json -nt "$marker" ]]; then
    log "Installing frontend dependencies..."
    (cd frontend && npm install)
  fi
}

ensure_running() {
  local pid="$1"
  local label="$2"

  if ! kill -0 "$pid" 2>/dev/null; then
    log "${label} stopped unexpectedly."
    wait "$pid" 2>/dev/null || true
    exit 1
  fi
}

wait_for_url() {
  local url="$1"
  local label="$2"

  if ! command -v curl >/dev/null 2>&1; then
    sleep 2
    return
  fi

  for _ in {1..90}; do
    if curl -fsS "$url" >/dev/null 2>&1; then
      return
    fi

    if [[ -n "$frontend_pid" ]]; then
      ensure_running "$frontend_pid" "Frontend"
    fi
    sleep 1
  done

  log "Warning: ${label} did not respond yet: ${url}"
}

require_command docker
ensure_frontend_deps
require_free_port "$FRONTEND_PORT" "Frontend"

log "Starting yarn-lab Docker stack..."
docker compose --profile yarn-lab up -d

log "Waiting for Flask backend: ${BACKEND_HEALTH_URL}"
wait_for_url "$BACKEND_HEALTH_URL" "Backend"

log "Starting Vite frontend: ${FRONTEND_URL}"
(
  cd frontend
  VITE_API_BASE_URL="$API_BASE_URL" npm run dev -- --port "$FRONTEND_PORT" --strictPort
) &
frontend_pid=$!

wait_for_url "$FRONTEND_URL" "Frontend"

if [[ "${OPEN_BROWSER:-1}" != "0" ]] && command -v open >/dev/null 2>&1; then
  open "$FRONTEND_URL"
fi

log "Frontend: ${FRONTEND_URL}"
log "Backend health: ${BACKEND_HEALTH_URL}"
log "API base: ${API_BASE_URL}"
log "YARN ResourceManager: http://127.0.0.1:${YARN_RM_UI_PORT:-18088}"
log "HDFS NameNode: http://127.0.0.1:${YARN_HDFS_UI_PORT:-19870}"
log "Spark History: http://127.0.0.1:${SPARK_HISTORY_UI_PORT:-28080}"
log "Press Ctrl+C to stop the frontend. Set STOP_DOCKER_ON_EXIT=1 to also stop Docker on exit."

while true; do
  sleep 1
  ensure_running "$frontend_pid" "Frontend"
done
