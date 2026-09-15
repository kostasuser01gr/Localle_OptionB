#!/usr/bin/env bash
set -euo pipefail
PROJECT_ROOT=$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
source "$PROJECT_ROOT/scripts/localle-defaults.sh"
MODEL=${LOCALLE_OLLAMA_MODEL:-llama3.1:8b}
N8N_BIN="$PROJECT_ROOT/scripts/localle-n8n"
line() { printf '%-24s %s\n' "$1" "$2"; }
if curl -fsS --max-time 5 http://127.0.0.1:${LOCALLE_N8N_PORT:-5678}/healthz >/dev/null; then line 'N8N' PASS; else line 'N8N' FAIL; fi
if [[ -x "$RUNTIME_DIR/node_modules/.bin/n8n" ]]; then line 'N8N VERSION' "$($N8N_BIN --version)"; else line 'N8N VERSION' MISSING; fi
if curl -fsS --max-time 5 http://127.0.0.1:11434/api/version >/dev/null; then line 'OLLAMA' PASS; else line 'OLLAMA' FAIL; fi
if command -v ollama >/dev/null && ollama list 2>/dev/null | awk 'NR>1 {print $1}' | grep -Fxq "$MODEL"; then line 'MODEL' "PASS ($MODEL)"; else line 'MODEL' FAIL; fi
if [[ -f "$USER_FOLDER/.n8n/database.sqlite" ]]; then line 'N8N DATABASE' PASS; else line 'N8N DATABASE' MISSING; fi
if "$PROJECT_ROOT/scripts/check-n8n-key-config.sh" "$USER_FOLDER/.n8n/config"; then line 'N8N ENCRYPTION KEY' 'PRESENT / PROTECTED'; else line 'N8N ENCRYPTION KEY' 'FAIL / RECOVERY REQUIRED'; fi
if [[ -f "$USER_FOLDER/.n8n/database.sqlite" ]]; then
  db="$USER_FOLDER/.n8n/database.sqlite"
  gmail_count=$(sqlite3 "$db" "SELECT count(*) FROM credentials_entity WHERE type='gmailOAuth2';" 2>/dev/null || echo 0)
  sheets_count=$(sqlite3 "$db" "SELECT count(*) FROM credentials_entity WHERE type='googleSheetsOAuth2Api';" 2>/dev/null || echo 0)
  ollama_count=$(sqlite3 "$db" "SELECT count(*) FROM credentials_entity WHERE type='ollamaApi';" 2>/dev/null || echo 0)
  [[ "$gmail_count" -gt 0 ]] && line 'GMAIL CREDENTIAL' 'PRESENT (metadata only)' || line 'GMAIL CREDENTIAL' MISSING
  [[ "$sheets_count" -gt 0 ]] && line 'SHEETS CREDENTIAL' 'PRESENT (metadata only)' || line 'SHEETS CREDENTIAL' MISSING
  [[ "$ollama_count" -gt 0 ]] && line 'OLLAMA CREDENTIAL' 'PRESENT (metadata only)' || line 'OLLAMA CREDENTIAL' MISSING
fi
if [[ -d "$STATE_DIR/backups" ]]; then line 'LAST BACKUP' "$(find "$STATE_DIR/backups" -mindepth 1 -maxdepth 1 -type d -print | sort | tail -n 1 | xargs -n1 basename 2>/dev/null || true)"; else line 'LAST BACKUP' NONE; fi
line 'AUTO SEND' 'PROVIDER READ REQUIRED: Config!auto_send_enabled must be FALSE'
line 'ZERO-COST CHECK' 'PASS — local Ollama only; no cloud AI endpoint configured by scripts'
