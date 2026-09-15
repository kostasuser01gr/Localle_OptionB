#!/usr/bin/env bash
# Validates local key configuration without printing, hashing, or exporting it.
set -euo pipefail

config=${1:?usage: check-n8n-key-config.sh /path/to/config}
[[ -f "$config" ]] || exit 1
node - "$config" <<'NODE'
const fs=require('fs');
try {
  const config=JSON.parse(fs.readFileSync(process.argv[2],'utf8'));
  if (typeof config.encryptionKey !== 'string' || config.encryptionKey.length < 32) process.exit(1);
} catch { process.exit(1); }
NODE
if [[ "$(uname -s)" == Darwin ]]; then mode=$(stat -f '%Lp' "$config"); else mode=$(stat -c '%a' "$config"); fi
[[ "$mode" == 600 ]] || exit 1
