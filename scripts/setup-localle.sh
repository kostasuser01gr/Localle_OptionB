#!/usr/bin/env bash
# Idempotent, zero-paid-AI setup. It installs only pinned n8n and llama3.1:8b.
set -euo pipefail

PROJECT_ROOT=$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
source "$PROJECT_ROOT/scripts/localle-defaults.sh"
MODEL=${LOCALLE_OLLAMA_MODEL:-llama3.1:8b}
WORKFLOW=$WORKFLOW_FILE
N8N_VERSION=1.117.3

"$PROJECT_ROOT/scripts/preflight-localle.sh" || {
  # A missing model is expected on first install; continue only if hardware/API are ready.
  command -v ollama >/dev/null 2>&1 && curl -fsS --max-time 5 http://127.0.0.1:11434/api/version >/dev/null || exit 1
}
command -v node >/dev/null 2>&1 || { echo 'Node.js 20+ is required.' >&2; exit 1; }
command -v npm >/dev/null 2>&1 || { echo 'npm is required.' >&2; exit 1; }
KEY_CONFIG_DIR="$USER_FOLDER/.n8n"
KEY_CONFIG="$KEY_CONFIG_DIR/config"
mkdir -p "$RUNTIME_DIR" "$USER_FOLDER" "$KEY_CONFIG_DIR"
chmod 700 "$KEY_CONFIG_DIR"

# A company state owns its own key. Never replace a present key and never
# generate a new one beside existing encrypted credentials.
if [[ ! -f "$KEY_CONFIG" ]]; then
  db="$KEY_CONFIG_DIR/database.sqlite"
  credential_rows=0
  if [[ -f "$db" ]] && command -v sqlite3 >/dev/null 2>&1; then
    credential_rows=$(sqlite3 "$db" 'SELECT count(*) FROM credentials_entity;' 2>/dev/null || echo 0)
  fi
  if [[ "$credential_rows" -gt 0 ]]; then
    echo 'Missing n8n encryption-key config beside existing credentials; stop and restore the original config/key.' >&2
    exit 1
  fi
  node - "$KEY_CONFIG" <<'NODE'
const crypto=require('crypto'),fs=require('fs');
const output=process.argv[2];
const config={encryptionKey:crypto.randomBytes(32).toString('base64')};
fs.writeFileSync(output,JSON.stringify(config,null,2)+'\n',{mode:0o600});
fs.chmodSync(output,0o600);
NODE
fi
chmod 600 "$KEY_CONFIG"
"$PROJECT_ROOT/scripts/check-n8n-key-config.sh" "$KEY_CONFIG" || { echo 'n8n encryption-key config is missing or has unsafe permissions.' >&2; exit 1; }

if [[ ! -x "$RUNTIME_DIR/node_modules/.bin/n8n" ]] || [[ "$("$RUNTIME_DIR/node_modules/.bin/n8n" --version 2>/dev/null || true)" != "$N8N_VERSION" ]]; then
  npm install --prefix "$RUNTIME_DIR" --omit=dev --no-audit --no-fund --package-lock=false "n8n@$N8N_VERSION"
fi
[[ "$("$RUNTIME_DIR/node_modules/.bin/n8n" --version)" == "$N8N_VERSION" ]] || { echo 'Pinned n8n verification failed.' >&2; exit 1; }

if ! ollama list | awk 'NR>1 {print $1}' | grep -Fxq "$MODEL"; then
  ollama pull "$MODEL"
fi
ollama list | awk 'NR>1 {print $1}' | grep -Fxq "$MODEL"
curl -fsS --max-time 120 http://127.0.0.1:11434/api/generate \
  -H 'Content-Type: application/json' \
  -d "{\"model\":\"$MODEL\",\"prompt\":\"Return exactly JSON with key health and boolean value true.\",\"format\":\"json\",\"stream\":false}" \
  | node -e 'let s="";process.stdin.on("data",d=>s+=d).on("end",()=>{const r=JSON.parse(s);JSON.parse(r.response);if(!r.done)process.exit(1);console.log("Local JSON inference PASS")})'

if [[ ! -f "$WORKFLOW" ]]; then echo "Workflow artifact missing: $WORKFLOW" >&2; exit 1; fi
echo 'Setup complete. Start Localle, create the three named company credentials in n8n, then run scripts/import-localle-workflow.sh. AUTO SEND remains OFF.'
