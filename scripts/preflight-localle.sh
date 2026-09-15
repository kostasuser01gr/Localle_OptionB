#!/usr/bin/env bash
set -euo pipefail

MODEL=${LOCALLE_OLLAMA_MODEL:-llama3.1:8b}
MIN_RAM_GIB=16
MIN_DISK_GIB=12
fail=0
report() { printf '%-24s %s\n' "$1" "$2"; }

os=$(uname -s)
arch=$(uname -m)
case "$os/$arch" in
  Darwin/arm64|Darwin/x86_64|Linux/x86_64|Linux/aarch64) report 'OS / architecture' "PASS ($os $arch)" ;;
  *) report 'OS / architecture' "FAIL (unsupported: $os $arch)"; fail=1 ;;
esac

if [[ "$os" == Darwin ]]; then
  ram_bytes=$(sysctl -n hw.memsize 2>/dev/null || echo 0)
  free_kib=$(df -Pk . | awk 'NR==2 {print $4}')
else
  ram_bytes=$(awk '/MemTotal/ {print $2*1024}' /proc/meminfo 2>/dev/null || echo 0)
  free_kib=$(df -Pk . | awk 'NR==2 {print $4}')
fi
ram_gib=$((ram_bytes / 1024 / 1024 / 1024))
disk_gib=$((free_kib / 1024 / 1024))
if (( ram_gib >= MIN_RAM_GIB )); then report 'RAM' "PASS (${ram_gib} GiB; minimum ${MIN_RAM_GIB} GiB)"; else report 'RAM' "FAIL (${ram_gib} GiB; need ${MIN_RAM_GIB} GiB)"; fail=1; fi
if (( disk_gib >= MIN_DISK_GIB )); then report 'Free disk' "PASS (${disk_gib} GiB; minimum ${MIN_DISK_GIB} GiB)"; else report 'Free disk' "FAIL (${disk_gib} GiB; need ${MIN_DISK_GIB} GiB)"; fail=1; fi

if command -v ollama >/dev/null 2>&1; then
  report 'Ollama executable' "PASS ($(ollama --version 2>/dev/null || true))"
  if curl -fsS --max-time 5 http://127.0.0.1:11434/api/version >/dev/null; then
    report 'Ollama local API' 'PASS'
    if ollama list 2>/dev/null | awk 'NR>1 {print $1}' | grep -Fxq "$MODEL"; then report 'Required model' "PASS ($MODEL)"; else report 'Required model' "FAIL (run scripts/setup-localle.sh)"; fail=1; fi
  else report 'Ollama local API' 'FAIL (start the local Ollama service)'; fail=1; fi
else report 'Ollama executable' 'FAIL (install Ollama from https://ollama.com/download)'; fail=1; fi

if (( fail )); then
  printf 'NO-GO / UNSUPPORTED HARDWARE OR RUNTIME\n' >&2
  exit 1
fi
