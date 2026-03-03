#!/usr/bin/env bash
# Stop the CMMC dev servers (backend on port 8081, frontend on port 9091)
set -euo pipefail

BACKEND_PORT=8081
FRONTEND_PORT=9091
stopped=0

stop_port() {
  local port=$1 label=$2
  local pids
  pids=$(lsof -ti :"$port" -sTCP:LISTEN 2>/dev/null || true)
  if [ -n "$pids" ]; then
    echo "Stopping $label (port $port) — PIDs: $pids"
    kill $pids 2>/dev/null || true
    stopped=1
  else
    echo "$label (port $port) is not running"
  fi
}

stop_port "$BACKEND_PORT" "backend"
stop_port "$FRONTEND_PORT" "frontend"

if [ "$stopped" -eq 1 ]; then
  # Brief wait then verify
  sleep 0.5
  remaining=$(lsof -ti :"$BACKEND_PORT" -ti :"$FRONTEND_PORT" -sTCP:LISTEN 2>/dev/null || true)
  if [ -n "$remaining" ]; then
    echo "Force-killing remaining PIDs: $remaining"
    kill -9 $remaining 2>/dev/null || true
  fi
  echo "Dev servers stopped."
else
  echo "No dev servers were running."
fi
