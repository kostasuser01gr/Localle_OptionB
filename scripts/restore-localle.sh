#!/usr/bin/env bash
set -euo pipefail
PROJECT_ROOT=$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
source "$PROJECT_ROOT/scripts/localle-defaults.sh"
if [[ "${1:-}" != '--from' || -z "${2:-}" ]]; then echo 'Usage: scripts/restore-localle.sh --from /path/to/backup' >&2; exit 2; fi
SOURCE=$2
[[ -f "$SOURCE/database.sqlite" && -f "$SOURCE/SHA256SUMS" ]] || { echo 'Invalid backup directory.' >&2; exit 1; }
(cd "$SOURCE" && shasum -a 256 -c SHA256SUMS)
if [[ -f "$STATE_DIR/n8n.pid" ]] && kill -0 "$(cat "$STATE_DIR/n8n.pid")" 2>/dev/null; then echo 'Stop Localle before restore.' >&2; exit 1; fi
DEST="$USER_FOLDER/.n8n/database.sqlite"
mkdir -p "$(dirname "$DEST")"
if [[ -f "$DEST" ]]; then mkdir -p "$STATE_DIR/pre-restore"; cp "$DEST" "$STATE_DIR/pre-restore/database-$(date +%Y%m%d_%H%M%S).sqlite"; fi
cp "$SOURCE/database.sqlite" "$DEST"
sqlite3 "$DEST" 'PRAGMA quick_check;' | grep -Fx ok
echo 'Restore complete. Workflow remains inactive until an authorized operator explicitly activates it in n8n.'
