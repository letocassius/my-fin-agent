#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUN_DIR="$ROOT_DIR/.run"

BACKEND_PID_FILE="$RUN_DIR/backend.pid"
FRONTEND_PID_FILE="$RUN_DIR/frontend.pid"

stop_from_pid_file() {
  local name="$1"
  local pid_file="$2"

  if [[ ! -f "$pid_file" ]]; then
    return
  fi

  local pid
  pid="$(cat "$pid_file")"

  if kill -0 "$pid" >/dev/null 2>&1; then
    kill "$pid"
    echo "Stopped $name (pid $pid)"
  fi

  rm -f "$pid_file"
}

stop_from_port() {
  local name="$1"
  local port="$2"
  local pids

  pids="$(lsof -ti "tcp:$port" || true)"
  if [[ -n "$pids" ]]; then
    echo "$pids" | xargs kill
    echo "Stopped $name on :$port"
  fi
}

stop_from_pid_file "backend" "$BACKEND_PID_FILE"
stop_from_pid_file "frontend" "$FRONTEND_PID_FILE"

stop_from_port "backend" "8000"
stop_from_port "frontend" "5173"
