#!/usr/bin/env bash
set -euo pipefail
PROJECT_ROOT=$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
source "$PROJECT_ROOT/scripts/localle-defaults.sh"
DB="$USER_FOLDER/.n8n/database.sqlite"
DEST="$STATE_DIR/backups/$(date +%Y%m%d_%H%M%S)"
[[ -f "$DB" ]] || { echo "No Localle database at $DB" >&2; exit 1; }
mkdir -p "$DEST"
sqlite3 "$DB" ".backup '$DEST/database.sqlite'"
cp "$WORKFLOW_FILE" "$DEST/workflow.json"
cp "$PROJECT_ROOT/config/live_sheet_contract.json" "$DEST/schema-manifest.json"
cp "$PROJECT_ROOT/RELEASE-MANIFEST.json" "$DEST/release-manifest.json"
shasum -a 256 "$DEST"/* > "$DEST/SHA256SUMS"
echo "Backup complete: $DEST"
