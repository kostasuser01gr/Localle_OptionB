#!/usr/bin/env bash
set -euo pipefail
PROJECT_ROOT=$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
"$PROJECT_ROOT/scripts/stop-localle.sh"
"$PROJECT_ROOT/scripts/start-localle.sh"
