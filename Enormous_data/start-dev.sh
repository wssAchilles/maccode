#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_PORT="${BACKEND_PORT:-5051}"
FRONTEND_PORT="${FRONTEND_PORT:-5173}"
BACKEND_HEALTH_URL="http://127.0.0.1:${BACKEND_PORT}/healthz"
FRONTEND_URL="http://127.0.0.1:${FRONTEND_PORT}/"

cd "$ROOT_DIR"

backend_pid=""
frontend_pid=""

log() {
  printf '[dev] %s\n' "$*"
}

fail() {
  printf '[dev] ERROR: %s\n' "$*" >&2
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

  if [[ -n "$backend_pid" ]] && kill -0 "$backend_pid" 2>/dev/null; then
    log "Stopping backend..."
    terminate_process_tree "$backend_pid"
  fi

  wait "$frontend_pid" "$backend_pid" 2>/dev/null || true
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

ensure_backend_deps() {
  require_command python3

  if [[ ! -x ".venv/bin/python" ]]; then
    log "Creating Python virtual environment..."
    python3 -m venv .venv
  fi

  local marker=".venv/.requirements-dev-installed"
  if [[ ! -f "$marker" || requirements.txt -nt "$marker" ]]; then
    log "Installing Python dependencies..."
    .venv/bin/python -m pip install -r requirements.txt
    touch "$marker"
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

  for _ in {1..30}; do
    if curl -fsS "$url" >/dev/null 2>&1; then
      return
    fi

    ensure_running "$backend_pid" "Backend"
    ensure_running "$frontend_pid" "Frontend"
    sleep 1
  done

  log "Warning: ${label} did not respond yet: ${url}"
}

ensure_backend_deps
ensure_frontend_deps
require_free_port "$BACKEND_PORT" "Backend"
require_free_port "$FRONTEND_PORT" "Frontend"

log "Starting Flask backend: http://127.0.0.1:${BACKEND_PORT}"
.venv/bin/flask --app run:app run --host 0.0.0.0 --port "$BACKEND_PORT" &
backend_pid=$!

log "Starting Vite frontend: ${FRONTEND_URL}"
(
  cd frontend
  VITE_API_BASE_URL="http://127.0.0.1:${BACKEND_PORT}/api/v1" npm run dev -- --port "$FRONTEND_PORT" --strictPort
) &
frontend_pid=$!

wait_for_url "$BACKEND_HEALTH_URL" "Backend"
wait_for_url "$FRONTEND_URL" "Frontend"

if [[ "${OPEN_BROWSER:-1}" != "0" ]] && command -v open >/dev/null 2>&1; then
  open "$FRONTEND_URL"
fi

log "Frontend: ${FRONTEND_URL}"
log "Backend health: ${BACKEND_HEALTH_URL}"
log "Press Ctrl+C to stop both services."

while true; do
  sleep 1
  ensure_running "$backend_pid" "Backend"
  ensure_running "$frontend_pid" "Frontend"
done
