#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
RID="smoke-rid-001"

cleanup() {
  if [[ -n "${STRAT_PID:-}" ]]; then
    kill "${STRAT_PID}" >/dev/null 2>&1 || true
    wait "${STRAT_PID}" 2>/dev/null || true
  fi
  if [[ -n "${GW_PID:-}" ]]; then
    kill "${GW_PID}" >/dev/null 2>&1 || true
    wait "${GW_PID}" 2>/dev/null || true
  fi
  docker stop cerberus-redis-smoke >/dev/null 2>&1 || true
}
trap cleanup EXIT

cd "${ROOT_DIR}"

docker run -d --rm --name cerberus-redis-smoke -p 6379:6379 redis:7.4-alpine >/dev/null

if [[ ! -d .venv ]]; then
  uv venv .venv --python 3.11 >/dev/null
fi
source .venv/bin/activate
uv sync --project services/strategy-py --all-groups --active >/dev/null

(
  REDIS_URL=redis://127.0.0.1:6379/0 \
    uv run --project services/strategy-py --active \
    uvicorn app.main:app --app-dir services/strategy-py --host 127.0.0.1 --port 8001 \
    >/tmp/cerberus-strategy.log 2>&1
) &
STRAT_PID=$!

(
  cd services/gateway-rs
  REDIS_URL=redis://127.0.0.1:6379/0 \
  STRATEGY_BASE_URL=http://127.0.0.1:8001 \
    cargo run >/tmp/cerberus-gateway.log 2>&1
) &
GW_PID=$!

echo "Waiting for services..."
for _ in {1..45}; do
  if curl -fsS http://127.0.0.1:8001/health >/dev/null 2>&1 && curl -fsS http://127.0.0.1:8080/health >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

assert_json_expr() {
  local file="$1"
  local expr="$2"
  python - "$file" "$expr" <<'PY'
import json
import sys
path = sys.argv[1]
expr = sys.argv[2]
with open(path, "r", encoding="utf-8") as fh:
    data = json.load(fh)
ok = eval(expr, {"data": data})  # noqa: S307
if not ok:
    raise SystemExit(f"assertion failed: {expr}\njson={data!r}")
PY
}

assert_header_equals() {
  local file="$1"
  local header="$2"
  local expected="$3"
  python - "$file" "$header" "$expected" <<'PY'
import sys
path, header, expected = sys.argv[1:4]
target = header.lower()
actual = ""
with open(path, "r", encoding="utf-8") as fh:
    for line in fh:
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        if key.strip().lower() == target:
            actual = value.strip()
            break
if actual != expected:
    raise SystemExit(f"header mismatch: {header}={actual!r}, expected {expected!r}")
PY
}

assert_file_contains() {
  local file="$1"
  local pattern="$2"
  python - "$file" "$pattern" <<'PY'
import sys
path, pattern = sys.argv[1:3]
with open(path, "r", encoding="utf-8") as fh:
    data = fh.read()
if pattern not in data:
    raise SystemExit(f"pattern not found: {pattern!r}")
PY
}

echo "Checking /ready endpoints..."
curl -fsS -D /tmp/strategy-ready-h -o /tmp/strategy-ready-b -H "x-request-id: ${RID}" \
  http://127.0.0.1:8001/ready >/dev/null
curl -fsS -D /tmp/gateway-ready-h -o /tmp/gateway-ready-b -H "x-request-id: ${RID}" \
  http://127.0.0.1:8080/ready >/dev/null
assert_header_equals /tmp/strategy-ready-h x-request-id "${RID}"
assert_header_equals /tmp/gateway-ready-h x-request-id "${RID}"
assert_json_expr /tmp/strategy-ready-b "data.get('ready') is True"
assert_json_expr /tmp/gateway-ready-b "data.get('ready') is True"

echo "Checking request-id propagation..."
curl -fsS -D /tmp/strategy-health-h -o /tmp/strategy-health-b -H "x-request-id: ${RID}" \
  http://127.0.0.1:8001/health >/dev/null
assert_header_equals /tmp/strategy-health-h x-request-id "${RID}"
assert_json_expr /tmp/strategy-health-b "data.get('status') == 'ok'"

curl -fsS -D /tmp/gateway-external-h -o /tmp/gateway-external-b -H "x-request-id: ${RID}" \
  http://127.0.0.1:8080/api/v1/external/status >/dev/null
assert_header_equals /tmp/gateway-external-h x-request-id "${RID}"
assert_json_expr /tmp/gateway-external-b "data.get('request_id') == 'smoke-rid-001'"

echo "Checking unified error envelope..."
curl -sS -D /tmp/strategy-err-h -o /tmp/strategy-err-b \
  -H "x-request-id: ${RID}" \
  -H "content-type: application/json" \
  -X POST http://127.0.0.1:8001/api/v1/matching/orders \
  --data '{"symbol":"BTCUSDT","side":"BUY","price":100,"quantity":0.01}' >/dev/null
assert_header_equals /tmp/strategy-err-h x-request-id "${RID}"
assert_json_expr /tmp/strategy-err-b "isinstance(data.get('error'), dict) and data['error'].get('request_id') == 'smoke-rid-001'"

curl -sS -D /tmp/gateway-err-h -o /tmp/gateway-err-b \
  -H "x-request-id: ${RID}" \
  -H "content-type: application/json" \
  -X POST http://127.0.0.1:8080/api/v1/binance/order/test \
  --data '{"symbol":"BTCUSDT","side":"BUY","order_type":"LIMIT","quantity":"0.001","price":"10000"}' >/dev/null
assert_header_equals /tmp/gateway-err-h x-request-id "${RID}"
assert_json_expr /tmp/gateway-err-b "isinstance(data.get('error'), dict) and data['error'].get('request_id') == 'smoke-rid-001'"

echo "Checking Prometheus /metrics endpoints..."
curl -fsS -D /tmp/strategy-metrics-h -o /tmp/strategy-metrics-b -H "x-request-id: ${RID}" \
  http://127.0.0.1:8001/metrics >/dev/null
curl -fsS -D /tmp/gateway-metrics-h -o /tmp/gateway-metrics-b -H "x-request-id: ${RID}" \
  http://127.0.0.1:8080/metrics >/dev/null
assert_header_equals /tmp/strategy-metrics-h x-request-id "${RID}"
assert_header_equals /tmp/gateway-metrics-h x-request-id "${RID}"
assert_file_contains /tmp/strategy-metrics-b "cerberus_strategy_up 1"
assert_file_contains /tmp/gateway-metrics-b "cerberus_gateway_up 1"

echo "Smoke test passed."
