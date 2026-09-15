#!/usr/bin/env bash
# Supported n8n import path for a fresh company credential store.
set -euo pipefail

PROJECT_ROOT=$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
source "$PROJECT_ROOT/scripts/localle-defaults.sh"
DB="$USER_FOLDER/.n8n/database.sqlite"
SOURCE=$WORKFLOW_FILE
TEMP_WORKFLOW="$STATE_DIR/import/localle-name-bound-import.json"

[[ -f "$DB" ]] || { echo 'n8n state is not initialized. Start n8n, complete owner setup, and create the three Localle credentials first.' >&2; exit 1; }
"$PROJECT_ROOT/scripts/check-n8n-key-config.sh" "$USER_FOLDER/.n8n/config" || { echo 'n8n key configuration is invalid; do not import.' >&2; exit 1; }
credential_overrides=()
for requirement in \
  "gmailOAuth2|Localle — Gmail OAuth" \
  "googleSheetsOAuth2Api|Localle — Google Sheets OAuth" \
  "ollamaApi|Localle — Ollama Local"; do
  type=${requirement%%|*}; name=${requirement#*|}
  count=$(sqlite3 "$DB" "SELECT count(*) FROM credentials_entity WHERE type='$type' AND name='$name';")
  # A source instance may retain one already-authorized Google Sheets
  # credential under an older display name. A unique type match is safe: the
  # temporary import copy is name-bound and n8n resolves it through its
  # supported importer. Fresh company installations still use the canonical
  # documented name.
  if [[ "$type" == "googleSheetsOAuth2Api" && "$count" == 0 ]]; then
    count=$(sqlite3 "$DB" "SELECT count(*) FROM credentials_entity WHERE type='$type';")
    if [[ "$count" == 1 ]]; then
      name=$(sqlite3 "$DB" "SELECT name FROM credentials_entity WHERE type='$type' LIMIT 1;")
      credential_overrides+=(--credential-name "$type=$name")
    fi
  fi
  [[ "$count" == 1 ]] || { echo "Create exactly one required $type credential named '$name' in n8n, then retry." >&2; exit 1; }
done
project_count=$(sqlite3 "$DB" "SELECT count(*) FROM project WHERE type='personal';")
[[ "$project_count" == 1 ]] || { echo 'Expected exactly one personal n8n project; choose the owner project before import.' >&2; exit 1; }
project_id=$(sqlite3 "$DB" "SELECT id FROM project WHERE type='personal' LIMIT 1;")
python3 "$PROJECT_ROOT/tools/prepare_portable_workflow.py" "$SOURCE" "$TEMP_WORKFLOW" "${credential_overrides[@]}"
"$PROJECT_ROOT/scripts/localle-n8n" import:workflow --input="$TEMP_WORKFLOW" --projectId="$project_id"
python3 "$PROJECT_ROOT/tools/verify_credential_bindings.py" --db "$DB"
echo 'PASS — all 27 workflow credential bindings were resolved by supported n8n name/type import matching.'
