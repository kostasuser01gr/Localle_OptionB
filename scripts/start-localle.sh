#!/usr/bin/env bash
set -euo pipefail
PROJECT_ROOT=$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
source "$PROJECT_ROOT/scripts/localle-defaults.sh"
PID_FILE="$STATE_DIR/n8n.pid"
LOG_FILE="$STATE_DIR/n8n.log"
mkdir -p "$STATE_DIR"
if [[ -f "$PID_FILE" ]] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then echo "Localle n8n already running (PID $(cat "$PID_FILE"))."; exit 0; fi
nohup "$PROJECT_ROOT/scripts/localle-n8n" start >>"$LOG_FILE" 2>&1 &
echo $! > "$PID_FILE"
for _ in $(seq 1 20); do
  if curl -fsS --max-time 1 "http://127.0.0.1:${LOCALLE_N8N_PORT:-5678}/healthz" >/dev/null 2>&1; then
    echo "Localle n8n started at http://127.0.0.1:${LOCALLE_N8N_PORT:-5678}"
    exit 0
  fi
  if ! kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
    echo "n8n exited during startup; inspect $LOG_FILE" >&2
    exit 1
  fi
  sleep 1
done
echo "n8n did not become ready within 20 seconds; inspect $LOG_FILE" >&2
exit 1
