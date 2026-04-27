#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STACK_DIR="$SCRIPT_DIR/veritas-ai"
LOCAL_PID_FILE="$SCRIPT_DIR/.friday-local.pid"

MODE="${MODE:-docker}"
ACTION="${1:-start}"

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || { echo "Missing required command: $1"; exit 1; }
}

wait_for_url() {
  local url="$1"
  local attempts="${2:-40}"
  local sleep_secs="${3:-2}"
  local i
  for ((i=1; i<=attempts; i++)); do
    if curl -fsS "$url" >/dev/null 2>&1; then
      return 0
    fi
    sleep "$sleep_secs"
  done
  return 1
}

docker_start() {
  require_cmd docker
  cd "$STACK_DIR"
  docker compose up --build -d
  echo "Waiting for backend readiness..."
  if wait_for_url "http://localhost:8001/api/v1/health" 45 2; then
    echo "FRIDAY is up."
    echo "Backend: http://localhost:8001/api/v1/health"
    echo "Frontend: http://localhost:3000"
  else
    echo "Backend did not become healthy in time."
    exit 1
  fi
}

docker_stop() {
  require_cmd docker
  cd "$STACK_DIR"
  docker compose down
}

docker_status() {
  require_cmd docker
  cd "$STACK_DIR"
  docker compose ps
}

docker_logs() {
  require_cmd docker
  cd "$STACK_DIR"
  docker compose logs -f --tail=200
}

local_start() {
  require_cmd python3
  cd "$STACK_DIR"
  nohup python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8001 > "$SCRIPT_DIR/.friday-local.log" 2>&1 &
  echo $! > "$LOCAL_PID_FILE"
  echo "Started local backend PID $(cat "$LOCAL_PID_FILE")"
  wait_for_url "http://localhost:8001/api/v1/health" 30 1 || {
    echo "Local backend failed readiness check"
    exit 1
  }
}

local_stop() {
  if [[ -f "$LOCAL_PID_FILE" ]]; then
    kill "$(cat "$LOCAL_PID_FILE")" >/dev/null 2>&1 || true
    rm -f "$LOCAL_PID_FILE"
    echo "Stopped local backend."
  else
    echo "No local pid file found."
  fi
}

local_status() {
  if [[ -f "$LOCAL_PID_FILE" ]] && kill -0 "$(cat "$LOCAL_PID_FILE")" >/dev/null 2>&1; then
    echo "Local backend running (PID $(cat "$LOCAL_PID_FILE"))."
  else
    echo "Local backend not running."
  fi
}

open_ui() {
  if command -v open >/dev/null 2>&1; then
    open "http://localhost:3000"
  else
    echo "Open http://localhost:3000 in your browser."
  fi
}

case "$ACTION" in
  start)
    if [[ "$MODE" == "local" ]]; then local_start; else docker_start; fi
    ;;
  stop)
    if [[ "$MODE" == "local" ]]; then local_stop; else docker_stop; fi
    ;;
  restart)
    "$0" stop
    "$0" start
    ;;
  status)
    if [[ "$MODE" == "local" ]]; then local_status; else docker_status; fi
    ;;
  logs)
    if [[ "$MODE" == "local" ]]; then
      tail -f "$SCRIPT_DIR/.friday-local.log"
    else
      docker_logs
    fi
    ;;
  open)
    open_ui
    ;;
  *)
    echo "Usage: $0 {start|stop|restart|status|logs|open}"
    echo "Optional: MODE=docker|local"
    exit 1
    ;;
esac
