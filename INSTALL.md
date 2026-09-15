# Localle installation

Localle uses local Ollama only and does not call a paid AI API.

Supported: macOS (Apple Silicon or Intel) or 64-bit Linux, 16 GiB RAM minimum (24–32 GiB recommended), 12 GiB free disk minimum (20 GiB recommended), Node.js 20+ with npm, and Ollama from <https://ollama.com/download>.

From the extracted release folder:

```bash
./scripts/setup-localle.sh
./scripts/start-localle.sh
```

The installer uses `~/.localle`, pins n8n to `1.117.3`, pulls only `llama3.1:8b` if absent, and generates a fresh local n8n encryption key with restrictive permissions. It never prints, packages, or silently replaces that key. It does not package model files, credentials, tokens, or a database. Tested hardware: macOS 26.3.1 on Apple Silicon, 16 GiB RAM, Ollama 0.31.2.

Windows is structurally prepared but not live-tested: `powershell -ExecutionPolicy Bypass -File scripts/windows/localle.ps1 -Action Setup`.
