# Troubleshooting

| Symptom | Action |
| --- | --- |
| `n8n` command not found | Do not install global n8n. Run `./scripts/setup-localle.sh`; use only `scripts/localle-n8n`. |
| Ollama API fails | Start Ollama and run `curl -s http://127.0.0.1:11434/api/version`. |
| Model missing | Run `./scripts/setup-localle.sh`; it pulls only `llama3.1:8b`. |
| n8n will not start | Run status and inspect `~/.localle/n8n.log`. |
| Gmail/Sheets authorization fails | Re-authorize approved credentials in n8n; never paste tokens into files or broaden scopes casually. |
| `import-localle-workflow.sh` says a credential is missing | In the local n8n UI, create exactly one credential of each required type with the exact names in `COMPANY-QUICKSTART.md`; then rerun the script. Do not edit workflow nodes or SQLite. |
| Encryption-key check fails | Stop n8n. If credentials already exist, restore the matching protected `.n8n/config`; never generate a replacement key beside the credential database. |
| Duplicate/uncertain delivery | Inspect `Human_Review` and Gmail Sent manually. Do not retry an uncertain send. |

Development-runtime diagnostics: `launchctl print gui/$(id -u)/com.kostas.ollama.serve`; `lsof -nP -iTCP:11434 -sTCP:LISTEN`; `tail -n 200 /tmp/ollama.log /tmp/ollama.err`.
