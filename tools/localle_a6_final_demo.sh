#!/usr/bin/env bash
set -euo pipefail

ROOT=$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
DB="$ROOT/.n8n-runtime/user/.n8n/database.sqlite"
SHEET='1j1hSY__8sCy7Ic4qHPaya3tzUqwQscEzlnKBv7JfbNc'

curl -fsS http://127.0.0.1:5678/healthz >/dev/null
curl -fsS http://127.0.0.1:11434/api/version >/dev/null
ollama list | rg '^llama3\.1:8b\s' >/dev/null
BASELINE=$(sqlite3 "$DB" "SELECT COALESCE(MAX(id),0) FROM execution_entity WHERE workflowId='LOCALLEOPTB2026A';")

# These URLs only prepare browser tabs. This script never invokes Gmail send.
open 'https://mail.google.com/mail/u/?authuser=userco000@gmail.com&view=cm&fs=1&to=kostasfoskolakis19@gmail.com&su=Localle%20demo%20reservation%20%E2%80%94%20Test%20Customer%20A6&body=Hello%2C%20my%20name%20is%20Test%20Customer%20A6.%0A%0AI%20need%20a%20small%20automatic%20car.%0A%0APickup%3A%20Kos%20Airport%2C%2018%20October%20at%2010%3A00.%0AReturn%3A%20Kos%20Airport%2C%2023%20October.%0A%0AMy%20phone%20is%20%2B30%20690%20000%200004.'
open "https://docs.google.com/spreadsheets/d/$SHEET/edit#gid=0&range=Config!A1"
open "https://docs.google.com/spreadsheets/d/$SHEET/edit#gid=0&range=Requests!A1"
open "https://docs.google.com/spreadsheets/d/$SHEET/edit#gid=0&range=Processed_Messages!A1"

echo '============================================================'
echo 'LOCALLE A6 STRICT E2E WATCHER'
echo 'A6 EMAIL: PREPARED — NOT SENT BY THIS SCRIPT'
echo 'Press Send in the prefilled Gmail compose after recording begins.'
echo '============================================================'
exec node "$ROOT/tools/localle_a6_final_demo.js" "$BASELINE"
