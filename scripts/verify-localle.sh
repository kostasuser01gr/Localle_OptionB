#!/usr/bin/env bash
set -euo pipefail
PROJECT_ROOT=$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
source "$PROJECT_ROOT/scripts/localle-defaults.sh"
MODEL=${LOCALLE_OLLAMA_MODEL:-llama3.1:8b}
"$PROJECT_ROOT/scripts/preflight-localle.sh"
"$PROJECT_ROOT/scripts/check-n8n-key-config.sh" "$USER_FOLDER/.n8n/config"
"$PROJECT_ROOT/scripts/localle-n8n" --version | grep -Fx '1.117.3'
node -e "JSON.parse(require('fs').readFileSync('$PROJECT_ROOT/config/live_sheet_contract.json')); console.log('Sheets schema manifest PASS')"
curl -fsS --max-time 120 http://127.0.0.1:11434/api/generate -H 'Content-Type: application/json' -d "{\"model\":\"$MODEL\",\"prompt\":\"Return exactly {\\\"health\\\":true}\",\"format\":\"json\",\"stream\":false}" | node -e 'let s="";process.stdin.on("data",d=>s+=d).on("end",()=>{const r=JSON.parse(s);JSON.parse(r.response);if(!r.done)process.exit(1);console.log("LOCAL INFERENCE PASS")})'
if [[ -f "$USER_FOLDER/.n8n/database.sqlite" ]]; then sqlite3 "$USER_FOLDER/.n8n/database.sqlite" 'PRAGMA quick_check;' | grep -Fx ok; fi
if [[ -f "$USER_FOLDER/.n8n/database.sqlite" ]]; then
  python3 "$PROJECT_ROOT/tools/verify_credential_bindings.py" --db "$USER_FOLDER/.n8n/database.sqlite" --allow-pending
fi
echo 'VERIFY PASS — Gmail/Sheets live authorization and Config!auto_send_enabled=FALSE require the controlled provider check in LIVE-E2E-EVIDENCE.md.'
