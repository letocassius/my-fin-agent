#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUN_DIR="$ROOT_DIR/.run"

BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"

BACKEND_PID_FILE="$RUN_DIR/backend.pid"
FRONTEND_PID_FILE="$RUN_DIR/frontend.pid"

BACKEND_LOG="$RUN_DIR/backend.log"
FRONTEND_LOG="$RUN_DIR/frontend.log"

mkdir -p "$RUN_DIR"

start_backend() {
  if lsof -ti tcp:8000 >/dev/null 2>&1; then
    echo "Backend already listening on :8000"
    return
  fi

  (
    cd "$BACKEND_DIR"
    nohup ./.venv/bin/uvicorn main:app --host 127.0.0.1 --port 8000 >>"$BACKEND_LOG" 2>&1 &
    echo $! >"$BACKEND_PID_FILE"
  )

  echo "Started backend on http://127.0.0.1:8000"
}

start_frontend() {
  if lsof -ti tcp:5173 >/dev/null 2>&1; then
    echo "Frontend already listening on :5173"
    return
  fi

  (
    cd "$FRONTEND_DIR"
    nohup npm run dev -- --host 127.0.0.1 >>"$FRONTEND_LOG" 2>&1 &
    echo $! >"$FRONTEND_PID_FILE"
  )

  echo "Started frontend on http://127.0.0.1:5173"
}

start_backend
start_frontend

echo "Logs:"
echo "  $BACKEND_LOG"
echo "  $FRONTEND_LOG"
