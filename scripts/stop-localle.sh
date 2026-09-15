#!/usr/bin/env bash
set -euo pipefail
PROJECT_ROOT=$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
source "$PROJECT_ROOT/scripts/localle-defaults.sh"
PID_FILE="$STATE_DIR/n8n.pid"
if [[ ! -f "$PID_FILE" ]]; then echo 'Localle n8n is not running.'; exit 0; fi
pid=$(cat "$PID_FILE")
if kill -0 "$pid" 2>/dev/null; then kill "$pid"; fi
rm -f "$PID_FILE"
echo 'Localle n8n stopped.'
