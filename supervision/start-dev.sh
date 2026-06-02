#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-4173}"
HOST="${HOST:-127.0.0.1}"
KILL_PORTS="${KILL_PORTS:-0}"

BACKEND_PID=""
FRONTEND_PID=""

print_info() {
  printf "\033[1;34m%s\033[0m\n" "$1"
}

print_error() {
  printf "\033[1;31m%s\033[0m\n" "$1" >&2
}

port_pids() {
  lsof -tiTCP:"$1" -sTCP:LISTEN 2>/dev/null || true
}

ensure_port_available() {
  local port="$1"
  local pids
  pids="$(port_pids "$port")"
  if [[ -z "$pids" ]]; then
    return 0
  fi

  if [[ "$KILL_PORTS" == "1" ]]; then
    print_info "端口 $port 已被占用，正在结束旧进程：$pids"
    kill $pids 2>/dev/null || true
    sleep 1
    return 0
  fi

  print_error "端口 $port 已被占用：$pids"
  print_error "请先停止旧服务，或使用：KILL_PORTS=1 ./start-dev.sh"
  exit 1
}

cleanup() {
  print_info "正在停止前后端服务..."
  if [[ -n "$FRONTEND_PID" ]]; then
    kill "$FRONTEND_PID" 2>/dev/null || true
  fi
  if [[ -n "$BACKEND_PID" ]]; then
    kill "$BACKEND_PID" 2>/dev/null || true
  fi
}

require_file() {
  if [[ ! -e "$1" ]]; then
    print_error "$2"
    exit 1
  fi
}

trap cleanup INT TERM EXIT

cd "$ROOT_DIR"

require_file "$ROOT_DIR/.venv/bin/python" "未找到项目虚拟环境：$ROOT_DIR/.venv。请先创建并安装 Python 依赖。"
require_file "$ROOT_DIR/frontend/package.json" "未找到前端项目：$ROOT_DIR/frontend/package.json"

if [[ ! -d "$ROOT_DIR/frontend/node_modules" ]]; then
  print_error "未找到 frontend/node_modules。请先执行：cd frontend && npm install"
  exit 1
fi

ensure_port_available "$BACKEND_PORT"
ensure_port_available "$FRONTEND_PORT"

print_info "启动 FastAPI 后端：http://$HOST:$BACKEND_PORT"
PYTHONPATH="$ROOT_DIR/backend" \
  "$ROOT_DIR/.venv/bin/python" -m uvicorn interfaces.api.app:app \
  --host "$HOST" \
  --port "$BACKEND_PORT" &
BACKEND_PID="$!"

print_info "启动 React/Vite 前端：http://$HOST:$FRONTEND_PORT"
(
  cd "$ROOT_DIR/frontend"
  npm run dev -- --host "$HOST" --port "$FRONTEND_PORT"
) &
FRONTEND_PID="$!"

print_info "前后端已启动。浏览器打开：http://$HOST:$FRONTEND_PORT"
print_info "按 Ctrl+C 可同时停止前后端。"

while true; do
  if ! kill -0 "$BACKEND_PID" 2>/dev/null; then
    print_error "后端进程已退出。"
    exit 1
  fi
  if ! kill -0 "$FRONTEND_PID" 2>/dev/null; then
    print_error "前端进程已退出。"
    exit 1
  fi
  sleep 1
done
